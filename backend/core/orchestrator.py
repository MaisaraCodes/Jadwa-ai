"""
Background LangGraph run kicked off by POST /applications/{id}/process.

Runs as a FastAPI BackgroundTask: in-process, after the 202 response is sent, on
the same event loop — no Celery/Redis, matching architecture.md's "no real
checkpointer, no extra infra" guidance for the hackathon build.

document_intelligence_node is still a STUB (separate ticket, Phase 2) — `_run_node`
paces it so the frontend's live-parse animation has a progress tick to show before
the real graph starts. Everything from `orchestrator_dispatch` onward is the real
compiled StateGraph in core/graph.py.
"""
from __future__ import annotations

import asyncio
import logging

from core import progress as progress_store
from core.graph import get_graph
from core.pipeline import ALL_NODES
from core.supabase import get_service_client
from models import ApplicationState, SMEProfile, UploadedFile

logger = logging.getLogger(__name__)

APPLICATIONS_TABLE = "applications"
SME_PROFILES_TABLE = "sme_profiles"
DOCUMENTS_TABLE = "application_documents"
AGENT_RESULTS_TABLE = "agent_results"

# Paces the demo's live-parse animation for the still-stubbed
# document_intelligence_node; delete this once that node lands for real.
STUB_NODE_SECONDS = 1.5


async def _run_node(node_name: str, application_id: str) -> None:
    # TODO(Phase 2): replace with the real document_intelligence_node call.
    await asyncio.sleep(STUB_NODE_SECONDS)


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
            storage_url=d["file_url"],
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


async def run_pipeline(application_id: str) -> None:
    progress_store.start(application_id)
    node_name = "document_intelligence_node"
    try:
        await _run_node(node_name, application_id)
        progress_store.mark_done(application_id, node_name)

        initial_state = await _build_initial_state(application_id)

        # stream_mode="updates" yields one chunk per finished node, keyed by
        # node name — that's what lets /status keep reporting live progress
        # instead of only finding out once the whole graph is done.
        async for update in get_graph().astream(initial_state, stream_mode="updates"):
            for node_name in update:
                if node_name in ALL_NODES:
                    progress_store.mark_done(application_id, node_name)
    except Exception:
        # Leave `status` at "processing" — /status will report a stalled
        # progress bar (nodes_completed short of ALL_NODES) instead of lying
        # about completion. The real fix is visible in the server logs.
        logger.exception(
            "Pipeline run failed for application_id=%s at node=%s",
            application_id,
            node_name,
        )
