"""
Background LangGraph run kicked off by POST /applications/{id}/process.

Runs as a FastAPI BackgroundTask: in-process, after the 202 response is sent, on
the same event loop — no Celery/Redis, matching architecture.md's "no real
checkpointer, no extra infra" guidance for the hackathon build.

document_intelligence_node is the real GPT-5.4 vision extraction (extract ->
normalize -> DocumentJSON, in the document_intelligence package). It runs here,
just before the compiled StateGraph, because architecture.md keeps it outside
the graph; everything from `orchestrator_dispatch` onward is the real compiled
StateGraph in core/graph.py.
"""
from __future__ import annotations

import asyncio
import logging

from core import progress as progress_store
from core.graph import get_graph
from core.pipeline import ALL_NODES
from core.supabase import get_service_client
from document_intelligence import document_intelligence_node
from models import ApplicationState, SMEProfile, UploadedFile

logger = logging.getLogger(__name__)

APPLICATIONS_TABLE = "applications"
SME_PROFILES_TABLE = "sme_profiles"
DOCUMENTS_TABLE = "application_documents"
AGENT_RESULTS_TABLE = "agent_results"


def _signed_document_url(svc, storage_path: str) -> str:
    """application_documents.file_url stores the bare Storage object path
    (routers/documents.py), not a fetchable URL — the vision model needs an
    actual URL it can GET, so re-sign it here the same way the upload
    response does."""
    from routers.documents import BUCKET, SIGNED_URL_TTL_SECONDS

    try:
        signed = svc.storage.from_(BUCKET).create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
    except Exception:
        return storage_path
    if isinstance(signed, dict):
        return signed.get("signedURL") or signed.get("signedUrl") or storage_path
    return getattr(signed, "signedURL", None) or getattr(signed, "signedUrl", None) or storage_path


async def _build_initial_state(application_id: str) -> ApplicationState:
    """Load the ApplicationState the compiled graph needs to run, and make
    sure the 4 agent nodes have an `agent_results` row to UPDATE into (each
    node writes only its own column — schema_mapping.md §2)."""
    svc = get_service_client()

    app_row = svc.table(APPLICATIONS_TABLE).select("*").eq("id", application_id).limit(1).execute().data[0]
    profile_row = (
        svc.table(SME_PROFILES_TABLE)
        .select("*")
        .eq("id", app_row["sme_profile_id"])
        .limit(1)
        .execute()
        .data[0]
    )
    doc_rows = svc.table(DOCUMENTS_TABLE).select("*").eq("application_id", application_id).execute().data or []

    sme_profile = SMEProfile.model_validate(profile_row)
    raw_documents = [
        UploadedFile(
            document_id=str(d["id"]),
            filename=d["filename"],
            storage_url=_signed_document_url(svc, d["file_url"]),
            content_type=d["file_type"],
        )
        for d in doc_rows
    ]

    svc.table(AGENT_RESULTS_TABLE).upsert({"application_id": application_id}).execute()

    return ApplicationState(
        application_id=application_id,
        sme_profile=sme_profile,
        raw_documents=raw_documents,
        extracted_documents=[],
        forensic_report=None,
        weakness_report=None,
        market_verdict=None,
        risk_baseline=None,
        unified_application_record=None,
    )


def _run_graph_sync(application_id: str, initial_state: ApplicationState) -> None:
    """The 4-way fan-out + aggregate, run to completion in a worker thread.

    The 4 agent nodes are plain sync functions doing blocking I/O (Postgres,
    OpenAI) — LangGraph does not offload sync nodes to a thread on its own,
    so driving them via the async `.astream()` API from the event-loop thread
    would block ALL concurrent request handling (including /status polling)
    for the entire graph run. Using the sync `.stream()` API here, itself
    wrapped in `asyncio.to_thread` by the caller, keeps the loop free the
    same way the document_intelligence_node call already does below.
    """
    for update in get_graph().stream(initial_state, stream_mode="updates"):
        for node_name in update:
            if node_name in ALL_NODES:
                progress_store.mark_done(application_id, node_name)


async def run_pipeline(application_id: str) -> None:
    progress_store.start(application_id)
    node_name = "document_intelligence_node"
    try:
        initial_state = await _build_initial_state(application_id)

        # Node 1 runs here, outside the graph (architecture.md §1). Its vision
        # calls are blocking, so run it in a worker thread to keep the event
        # loop free for the /status poller. Its output is fed into the state
        # the graph then reads from (the 4 agent nodes consume
        # extracted_documents).
        node_output = await asyncio.to_thread(document_intelligence_node, initial_state)
        initial_state["extracted_documents"] = node_output["extracted_documents"]
        progress_store.mark_done(application_id, node_name)

        # Same reasoning as above: the graph's own nodes block just as hard,
        # so this also runs off the event loop.
        await asyncio.to_thread(_run_graph_sync, application_id, initial_state)

        # Lifecycle transition: processing → review_ready (architecture.md §4).
        # Written here so the status is reload-safe server state — the SME portal
        # can poll /status and get the correct final state even after a page refresh.
        get_service_client().table(APPLICATIONS_TABLE).update(
            {"status": "review_ready"}
        ).eq("id", application_id).execute()

    except Exception:
        # Leave `status` at "processing" — /status will report a stalled
        # progress bar (nodes_completed short of ALL_NODES) instead of lying
        # about completion. The real fix is visible in the server logs.
        logger.exception(
            "Pipeline run failed for application_id=%s at node=%s",
            application_id,
            node_name,
        )
