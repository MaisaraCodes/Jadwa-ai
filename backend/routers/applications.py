"""
SME portal — application lifecycle (docs/API_CONTRACT.md).

    POST  /api/v1/applications                                  REAL
    GET   /api/v1/applications                                  REAL
    POST  /api/v1/applications/{id}/process                     STUB
    GET   /api/v1/applications/{id}/status                      STUB
    GET   /api/v1/applications/{id}/extracted                   REAL
    PATCH /api/v1/applications/{id}/documents/{document_id}     REAL
    POST  /api/v1/applications/{id}/submit                      REAL
    GET   /api/v1/applications/{id}/summary                     STUB
    GET   /api/v1/applications/{id}/pdf                          REAL

Ownership resolves auth user -> sme_profiles row -> applications.sme_profile_id, same
pattern (and the same helpers) as routers/documents.py — imported from there rather than
re-implemented, so the two routers can never drift on ownership semantics.

Node-output fields (forensic_report, weakness_report, business_model_score, ...) are
`null`/placeholder until the Phase-2 LangGraph nodes populate `agent_results` — see the
STUB markers below for exactly which Phase-2/4 node fills each one.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date as _date

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from core import progress as progress_store
from core.application_builder import ensure_application_pdf
from core.auth import Principal, require_sme
from core.errors import APIError
from core.orchestrator import run_pipeline
from core.pipeline import ALL_NODES, TERMINAL_STATUSES
from core.supabase import get_service_client
from models import ApplicationFinancing, ApplicationStatus, DocumentJSON, WeaknessReport
from routers.documents import (
    APPLICATIONS_ID_COL,
    APPLICATIONS_OWNER_COL,
    APPLICATIONS_TABLE,
    _assert_owned_application,
    _caller_profile_id,
    _signed_url,
)

AGENT_RESULTS_TABLE = "agent_results"
DOCUMENTS_TABLE = "application_documents"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


# --- request/response DTOs (shapes not already in models.py) ---------------
class CreateApplicationRequest(BaseModel):
    requested_amount: float | None = None
    # financing detail fields (migration 004)
    amount: float | None = None
    purpose: str | None = None
    term_months: int | None = None
    description: str | None = None


class CreateApplicationResponse(BaseModel):
    application_id: str
    status: ApplicationStatus


class ApplicationSummaryItem(BaseModel):
    application_id: str
    status: ApplicationStatus
    created_at: str
    document_count: int
    amount: float | None = None


class ListApplicationsResponse(BaseModel):
    applications: list[ApplicationSummaryItem]


class ProcessResponse(BaseModel):
    status: ApplicationStatus


class StatusResponse(BaseModel):
    status: ApplicationStatus
    nodes_completed: list[str]
    progress: float


class ExtractedDocumentsResponse(BaseModel):
    documents: list[DocumentJSON]


class PatchDocumentRequest(BaseModel):
    extracted_amount: float | None = None
    date: _date | None = None
    vendor: str | None = None
    type: str | None = None


class SubmitResponse(BaseModel):
    status: ApplicationStatus


class SummaryResponse(BaseModel):
    health_summary: str
    business_model_score: int | None
    top_risks: list[str]


class PdfResponse(BaseModel):
    pdf_url: str | None


# --- helpers -----------------------------------------------------------------
def _get_application(svc, application_id: str) -> dict:
    res = (
        svc.table(APPLICATIONS_TABLE)
        .select("*")
        .eq(APPLICATIONS_ID_COL, application_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise APIError(404, "application_not_found", "No application with that id.")
    return rows[0]


def _get_agent_results(svc, application_id: str) -> dict:
    res = (
        svc.table(AGENT_RESULTS_TABLE)
        .select("*")
        .eq("application_id", application_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else {}


# --- POST /applications -------------------------------------------------------
@router.post("", status_code=201, response_model=CreateApplicationResponse)
async def create_application(
    body: CreateApplicationRequest,
    principal: Principal = Depends(require_sme),
) -> CreateApplicationResponse:
    svc = get_service_client()
    profile_id = _caller_profile_id(svc, principal.user_id)

    try:
        res = (
            svc.table(APPLICATIONS_TABLE)
            .insert(
                {
                    APPLICATIONS_OWNER_COL: profile_id,
                    "requested_amount": body.requested_amount or 0,
                    "status": "draft",
                    # financing fields — NULL when not supplied
                    "amount": body.amount,
                    "purpose": body.purpose,
                    "term_months": body.term_months,
                    "description": body.description,
                }
            )
            .execute()
        )
    except Exception:
        raise APIError(500, "db_error", "Could not create the application.")

    rows = res.data or []
    if not rows:
        raise APIError(500, "db_error", "Application was not created.")
    return CreateApplicationResponse(application_id=str(rows[0][APPLICATIONS_ID_COL]), status="draft")


# --- GET /applications ---------------------------------------------------------
@router.get("", response_model=ListApplicationsResponse)
async def list_applications(principal: Principal = Depends(require_sme)) -> ListApplicationsResponse:
    svc = get_service_client()
    profile_id = _caller_profile_id(svc, principal.user_id)

    res = (
        svc.table(APPLICATIONS_TABLE)
        .select(f"{APPLICATIONS_ID_COL},status,created_at,amount")
        .eq(APPLICATIONS_OWNER_COL, profile_id)
        .order("created_at", desc=True)
        .execute()
    )
    apps = res.data or []
    app_ids = [a[APPLICATIONS_ID_COL] for a in apps]

    counts: dict[str, int] = {}
    if app_ids:
        doc_res = (
            svc.table(DOCUMENTS_TABLE)
            .select("application_id")
            .in_("application_id", app_ids)
            .execute()
        )
        for row in doc_res.data or []:
            aid = str(row["application_id"])
            counts[aid] = counts.get(aid, 0) + 1

    items = [
        ApplicationSummaryItem(
            application_id=str(a[APPLICATIONS_ID_COL]),
            status=a["status"],
            created_at=str(a["created_at"]),
            document_count=counts.get(str(a[APPLICATIONS_ID_COL]), 0),
            amount=a.get("amount"),
        )
        for a in apps
    ]
    return ListApplicationsResponse(applications=items)


# --- POST /applications/{id}/process -------------------------------------------
@router.post("/{application_id}/process", status_code=202, response_model=ProcessResponse)
async def process_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_sme),
) -> ProcessResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    app = _get_application(svc, application_id)
    if app["status"] != "draft":
        raise APIError(
            409,
            "already_processed",
            "This application has already been processed or submitted.",
        )

    svc.table(APPLICATIONS_TABLE).update({"status": "processing"}).eq(
        APPLICATIONS_ID_COL, application_id
    ).execute()

    # Kicks off the LangGraph run in-process, after this response is sent
    # (architecture.md — no checkpointer/queue infra for the hackathon build).
    background_tasks.add_task(run_pipeline, application_id)

    return ProcessResponse(status="processing")


# --- GET /applications/{id}/status ----------------------------------------------
@router.get("/{application_id}/status", response_model=StatusResponse)
async def application_status(
    application_id: str,
    principal: Principal = Depends(require_sme),
) -> StatusResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    app = _get_application(svc, application_id)
    status = app["status"]

    if status in TERMINAL_STATUSES:
        # Pipeline definitely ran (possibly in an earlier server process, so the
        # in-memory tracker may know nothing about it) — report all nodes done.
        nodes_completed = list(ALL_NODES)
    elif status == "processing":
        nodes_completed = progress_store.get_nodes_completed(application_id)
    else:
        # "draft" — /process hasn't been called yet.
        nodes_completed = []

    progress = len(nodes_completed) / len(ALL_NODES)
    return StatusResponse(status=status, nodes_completed=nodes_completed, progress=progress)


# --- GET /applications/{id}/extracted -------------------------------------------
@router.get("/{application_id}/extracted", response_model=ExtractedDocumentsResponse)
async def extracted_documents(
    application_id: str,
    principal: Principal = Depends(require_sme),
) -> ExtractedDocumentsResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    agent_results = _get_agent_results(svc, application_id)
    raw_docs = agent_results.get("extracted_documents") or []
    docs = [DocumentJSON.model_validate(d) for d in raw_docs]
    return ExtractedDocumentsResponse(documents=docs)


# --- PATCH /applications/{id}/documents/{document_id} ---------------------------
@router.patch("/{application_id}/documents/{document_id}")
async def patch_extracted_document(
    application_id: str,
    document_id: str,
    body: PatchDocumentRequest,
    principal: Principal = Depends(require_sme),
) -> dict:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    agent_results = _get_agent_results(svc, application_id)
    raw_docs: list[dict] = agent_results.get("extracted_documents") or []

    target = None
    for d in raw_docs:
        if str(d.get("document_id")) == document_id:
            target = d
            break
    if target is None:
        raise APIError(404, "document_not_found", "No extracted document with that id.")

    if body.extracted_amount is not None:
        target["extracted_amount"] = body.extracted_amount
    if body.date is not None:
        target["date"] = body.date.isoformat()
    if body.vendor is not None:
        target["vendor"] = body.vendor
    if body.type is not None:
        target["type"] = body.type

    try:
        svc.table(AGENT_RESULTS_TABLE).update({"extracted_documents": raw_docs}).eq(
            "application_id", application_id
        ).execute()
    except Exception:
        raise APIError(500, "db_error", "Could not save the document update.")

    return target


# --- POST /applications/{id}/submit ---------------------------------------------
@router.post("/{application_id}/submit", response_model=SubmitResponse)
async def submit_application(
    application_id: str,
    principal: Principal = Depends(require_sme),
) -> SubmitResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    svc.table(APPLICATIONS_TABLE).update({"status": "review_ready"}).eq(
        APPLICATIONS_ID_COL, application_id
    ).execute()

    # Build the final PDF now (API_CONTRACT: submit "runs application_builder
    # if not already"). Idempotent — ensure_application_pdf serves the cached
    # object when it exists — and best-effort: a build failure must not fail
    # the submit, because GET /pdf rebuilds on demand and surfaces the error
    # there. Off the event loop: WeasyPrint blocks for seconds.
    try:
        await asyncio.to_thread(ensure_application_pdf, application_id)
    except Exception:
        logger.exception(
            "submit: PDF build failed for application_id=%s (deferred to GET /pdf)",
            application_id,
        )

    return SubmitResponse(status="review_ready")


# --- GET /applications/{id}/summary ---------------------------------------------
@router.get("/{application_id}/summary", response_model=SummaryResponse)
async def application_summary(
    application_id: str,
    principal: Principal = Depends(require_sme),
) -> SummaryResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    agent_results = _get_agent_results(svc, application_id)
    raw_weakness = agent_results.get("weakness_report") or {}

    # STUB — Phase-2 devils_advocate_node writes weakness_report; until then this
    # is a placeholder with a null score.
    if raw_weakness:
        weakness = WeaknessReport.model_validate(raw_weakness)
        return SummaryResponse(
            health_summary="Analysis complete.",
            business_model_score=weakness.business_model_score,
            top_risks=weakness.critical_weaknesses,
        )
    return SummaryResponse(
        health_summary="Analysis pending — this application has not been processed yet.",
        business_model_score=None,
        top_risks=[],
    )


# --- GET /applications/{id}/pdf --------------------------------------------------
@router.get("/{application_id}/pdf", response_model=PdfResponse)
async def application_pdf(
    application_id: str,
    principal: Principal = Depends(require_sme),
) -> PdfResponse:
    svc = get_service_client()
    _assert_owned_application(svc, application_id, principal.user_id)

    # Self-healing: ensure_application_pdf serves the cached Storage object when
    # final_pdf_url points at a real one, and otherwise builds the report NOW
    # from the stored analysis (seeded/backfilled apps reach review_ready
    # without ever running the graph — the PDF is decoupled from the lifecycle).
    # The bare object path is signed here so the contract's "signed Supabase
    # Storage URL" (architecture.md §4) is what actually goes out. Still null
    # when there is no analysis to report on yet. Off the event loop:
    # WeasyPrint blocks for seconds.
    _get_application(svc, application_id)  # 404 if missing
    try:
        storage_path = await asyncio.to_thread(ensure_application_pdf, application_id)
    except Exception:
        logger.exception(
            "GET /pdf: report build failed for application_id=%s", application_id
        )
        raise APIError(
            500,
            "pdf_build_failed",
            "The final report could not be generated for this application.",
        )
    if not storage_path:
        return PdfResponse(pdf_url=None)
    return PdfResponse(pdf_url=_signed_url(svc, storage_path))
