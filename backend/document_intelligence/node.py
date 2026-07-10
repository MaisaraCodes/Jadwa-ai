"""
document_intelligence_node — Node 1 of the pipeline (architecture.md §1).

Reads `raw_documents` (the uploaded files) off ApplicationState and writes
`extracted_documents: list[DocumentJSON]`. Per architecture.md this node is NOT
inside the compiled StateGraph (core/graph.py) — it runs in core/orchestrator.py
just before the graph, feeding the four agent nodes their input.

Two-stage per file: extract.py does the GPT-5.4 vision read (file -> raw dict),
normalize.py coerces that into a canonical DocumentJSON. Both stages are
crash-proof by construction (extract returns {} on failure; normalize returns
None only if Pydantic rejects even the defaulted shape), so one bad file lowers
that document's confidence or drops just that document — it never sinks the run.

The node is a plain (sync) function matching the graph-node signature so it
stays unit-testable without an event loop; the orchestrator invokes it via
asyncio.to_thread so the blocking vision calls don't stall the loop.
"""
from __future__ import annotations

import logging

from core.supabase import get_service_client
from document_intelligence.extract import extract_document_fields
from document_intelligence.normalize import normalize_extracted_document
from models import ApplicationState, DocumentJSON

logger = logging.getLogger(__name__)

AGENT_RESULTS_TABLE = "agent_results"
EXTRACTED_COLUMN = "extracted_documents"


def _persist_extracted_documents(application_id: str, documents: list[DocumentJSON]) -> None:
    """UPDATEs agent_results.extracted_documents (schema_mapping.md §2 — each
    node writes its own column as soon as it finishes). Wrapped in try/except
    like the graph nodes' _persist_column: a DB hiccup here must not crash the
    node, since the value is also carried forward in graph state regardless."""
    payload = [doc.model_dump(mode="json") for doc in documents]
    try:
        get_service_client().table(AGENT_RESULTS_TABLE).update(
            {EXTRACTED_COLUMN: payload}
        ).eq("application_id", application_id).execute()
    except Exception:
        logger.exception(
            "Failed to persist %s for application_id=%s", EXTRACTED_COLUMN, application_id
        )


def document_intelligence_node(state: ApplicationState) -> dict:
    """Extracts + normalizes every uploaded file into DocumentJSONs.

    Returns {"extracted_documents": [...]} for the graph state. Documents that
    fail Pydantic validation even after normalization (normalize returns None)
    are logged and skipped here — the batch proceeds with whatever validated,
    and the dropped ones surface as a shortfall the caller can flag for manual
    review.
    """
    application_id = state["application_id"]
    raw_documents = state.get("raw_documents", [])

    extracted: list[DocumentJSON] = []
    for uploaded in raw_documents:
        raw_fields = extract_document_fields(uploaded)
        doc = normalize_extracted_document(raw_fields, uploaded.document_id)
        if doc is None:
            logger.warning(
                "document_intelligence: dropped unvalidatable document_id=%s "
                "(application_id=%s) — flag for manual review",
                uploaded.document_id, application_id,
            )
            continue
        extracted.append(doc)

    _persist_extracted_documents(application_id, extracted)
    logger.info(
        "document_intelligence: extracted %d/%d document(s) for application_id=%s",
        len(extracted), len(raw_documents), application_id,
    )
    return {"extracted_documents": extracted}


__all__ = ["document_intelligence_node"]
