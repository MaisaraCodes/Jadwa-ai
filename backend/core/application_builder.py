"""
application_builder_node — the Arabic PDF that renders a completed application
(architecture.md §1; CONVENTIONS.md node table: reads `unified_application_record`,
WeasyPrint, no LLM).

The PDF is the artifact the BANK reads, so it uses the bank accent (falcon blue,
DESIGN_SYSTEM.md §4) even though the SME can download it. Five sections, fixed
order: SME profile → forensic → weakness → market → risk baseline.

Determinism (the demo must be repeatable): same ApplicationRecord in → byte-identical
PDF out. That means NO wall-clock anywhere — not in the PDF metadata (see
`_PDF_METADATA_EPOCH` below) and not in the cover date, which is derived from the
newest extracted document rather than from `today` (see `latest_document_date`).

WeasyPrint is imported LAZILY, inside `render_pdf_bytes`. It needs the native
Pango/GTK stack, which is absent on a stock Windows box — a module-level
`import weasyprint` would make `core.graph` (and therefore the whole FastAPI app
and every existing test) unimportable there. Importing it only when a PDF is
actually rendered keeps the graph importable everywhere and confines the native
dependency to the one call that truly needs it.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.supabase import get_service_client
from models import ApplicationRecord, ApplicationState

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "application_report.html"

# Storage: reuse the existing private bucket (migrations/001) rather than
# standing up a second one — the backend mediates every read via signed URLs, so
# a new bucket would buy nothing but another RLS surface. The uploaded documents
# live at {application_id}/{document_id}/{filename}; the generated report sits
# beside them at {application_id}/report.pdf.
PDF_BUCKET = "application-documents"
PDF_CONTENT_TYPE = "application/pdf"

APPLICATIONS_TABLE = "applications"
APPLICATIONS_ID_COL = "id"
# GET /applications/{id}/pdf already reads this column (routers/applications.py).
# It stores the bare Storage object path — same convention as
# application_documents.file_url — and the endpoint signs it on read.
PDF_URL_COLUMN = "final_pdf_url"

# Fixed PDF /CreationDate + /ModDate. WeasyPrint only emits these when the
# document supplies them, but pinning them explicitly makes the determinism
# guarantee a property of THIS module rather than of WeasyPrint's default. The
# value is arbitrary and deliberately not "now" — a PDF that re-renders to
# different bytes every run cannot be diffed or cached.
_PDF_METADATA_EPOCH = "2025-01-01T00:00:00Z"

# The same instant as _PDF_METADATA_EPOCH, for fontTools.
#
# WeasyPrint subsets the bundled fonts with fontTools, and fontTools stamps the
# subsetted font's `head.modified` field with the current time — which lands
# INSIDE the PDF's embedded font stream. That alone makes two renders of an
# identical record differ by ~30KB of font bytes. fontTools honours the
# reproducible-builds SOURCE_DATE_EPOCH convention, so pinning it here is what
# actually buys byte-identical output; the fixed /CreationDate above is not
# enough on its own. Verified by test_identical_record_renders_identical_bytes.
#
# setdefault, not a plain assignment: a caller doing a genuine reproducible
# build already sets this, and their value should win.
_SOURCE_DATE_EPOCH = "1735689600"  # 2025-01-01T00:00:00Z
os.environ.setdefault("SOURCE_DATE_EPOCH", _SOURCE_DATE_EPOCH)

# --- Arabic label maps -------------------------------------------------------
# The PDF is Arabic-primary (all-Arabic for the demo; the SME-side AR/EN toggle
# is deferred). Domain literals come from models.py and are mapped 1:1 here.
FORENSIC_STATUS_LABELS = {
    "green": "مطابق",
    "yellow": "يحتاج مراجعة",
    "red": "مُعلَّم",
}
# green/yellow/red → pass/review/flag (DESIGN_SYSTEM.md §9). This is the one
# place those tokens are correct: forensic status is exactly what they encode.
FORENSIC_STATUS_TOKENS = {"green": "pass", "yellow": "review", "red": "flag"}

SEVERITY_LABELS = {"high": "مرتفعة", "medium": "متوسطة", "low": "منخفضة"}
# Severity high/medium/low → flag/review/text-2 (DESIGN_SYSTEM.md §9).
SEVERITY_TOKENS = {"high": "flag", "medium": "review", "low": "muted"}

SECTOR_TREND_LABELS = {"growing": "نمو", "stable": "استقرار", "declining": "تراجع"}
SATURATION_LABELS = {"low": "منخفض", "medium": "متوسط", "high": "مرتفع"}

NOT_AVAILABLE = "غير متوفر لهذا الطلب"


# --- formatting helpers ------------------------------------------------------
# Every figure is Western digits + tabular numbers, wrapped dir="ltr" by the
# template where it sits in an Arabic run (DESIGN_SYSTEM.md §3.2).
def format_percent(value: float | None, decimals: int = 1) -> str:
    """0.85 -> '85.0%'. None -> an em dash, never 'None'."""
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def latest_document_date(record: ApplicationRecord) -> date | None:
    """The newest extracted document's date — the cover's 'as of' date.

    Deliberately NOT `date.today()`: the cover date has to be a function of the
    record, or the same application renders to different bytes tomorrow and the
    determinism guarantee (and the repeatable demo) is gone. None when the
    record has no documents, in which case the template omits the line rather
    than inventing one.
    """
    dates = [d.date for d in record.extracted_documents if d.date]
    return max(dates) if dates else None


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_context(record: ApplicationRecord) -> dict:
    """Flatten an ApplicationRecord into what the template reads.

    Each of the four agent sections can be None on a partial record (models.py),
    so each is passed through as-is and the template branches on it — a partial
    record renders a complete PDF with 'not available' notes, never a crash.
    """
    forensic = record.forensic_report
    return {
        "record": record,
        "profile": record.sme_profile,
        "forensic": forensic,
        "weakness": record.weakness_report,
        "market": record.market_verdict,
        "risk": record.risk_baseline,
        "forensic_status_label": FORENSIC_STATUS_LABELS.get(forensic.overall_status) if forensic else None,
        "forensic_status_token": FORENSIC_STATUS_TOKENS.get(forensic.overall_status) if forensic else None,
        "severity_labels": SEVERITY_LABELS,
        "severity_tokens": SEVERITY_TOKENS,
        "sector_trend_labels": SECTOR_TREND_LABELS,
        "saturation_labels": SATURATION_LABELS,
        "not_available": NOT_AVAILABLE,
        "cover_date": latest_document_date(record),
        "metadata_epoch": _PDF_METADATA_EPOCH,
        "format_percent": format_percent,
        "format_number": format_number,
    }


def render_html(record: ApplicationRecord) -> str:
    """The template render, split out from the PDF render so tests (and a human
    eyeballing the layout in a browser) can inspect the markup without needing
    WeasyPrint's native stack."""
    return _jinja_env().get_template(TEMPLATE_NAME).render(**build_context(record))


def render_pdf_bytes(record: ApplicationRecord) -> bytes:
    """ApplicationRecord -> PDF bytes. Deterministic for a given WeasyPrint version.

    `base_url` points at the template file so the @font-face `url('fonts/...')`
    references resolve against templates/fonts/ — WeasyPrint loads the bundled
    TTFs off disk, with no network fetch and no dependency on a system font
    being installed.
    """
    from weasyprint import HTML  # lazy: see module docstring

    html = render_html(record)
    return HTML(string=html, base_url=str(TEMPLATES_DIR / TEMPLATE_NAME)).write_pdf()


def pdf_storage_path(application_id: str) -> str:
    return f"{application_id}/report.pdf"


def upload_pdf(application_id: str, pdf_bytes: bytes) -> str:
    """Upload to the private bucket and return the bare object path.

    `upsert` is on: re-processing an application overwrites its report in place
    rather than erroring or orphaning the previous object.
    """
    path = pdf_storage_path(application_id)
    get_service_client().storage.from_(PDF_BUCKET).upload(
        path,
        pdf_bytes,
        {"content-type": PDF_CONTENT_TYPE, "upsert": "true"},
    )
    return path


def persist_pdf_path(application_id: str, storage_path: str) -> None:
    get_service_client().table(APPLICATIONS_TABLE).update(
        {PDF_URL_COLUMN: storage_path}
    ).eq(APPLICATIONS_ID_COL, application_id).execute()


def application_builder_node(state: ApplicationState) -> dict:
    """Render the completed application to a PDF and file it (architecture.md §1).

    Writes ONLY `final_pdf_url` on the state (CONVENTIONS.md rule 5) — the bare
    Storage object path, which is also what lands in applications.final_pdf_url
    for GET /applications/{id}/pdf to sign.

    This node does NOT touch the lifecycle status, despite the architecture.md
    node table's "final PDF + status update". `submitted` is not a valid DB enum
    value (architecture.md §4 says so explicitly), and the one real transition —
    processing → review_ready — is already owned by core/orchestrator.py once the
    whole graph completes. Advancing it here would either duplicate that write or
    invent a status. See the ticket's Section K.

    Never raises: a Storage or DB failure downgrades to `final_pdf_url: None` and
    a logged exception. The PDF is a derived artifact — the unified record is
    already persisted by aggregate_results_node, and failing the whole graph over
    a missing convenience download would lose the analysis that actually matters.
    """
    record = state.get("unified_application_record")
    if record is None:
        # aggregate_results_node is this node's only upstream edge, so this means
        # the merge itself failed. Nothing to render.
        logger.error(
            "application_builder_node: no unified_application_record for application_id=%s",
            state.get("application_id"),
        )
        return {"final_pdf_url": None}

    application_id = state["application_id"]
    try:
        pdf_bytes = render_pdf_bytes(record)
        storage_path = upload_pdf(application_id, pdf_bytes)
        persist_pdf_path(application_id, storage_path)
    except Exception:
        logger.exception(
            "application_builder_node: PDF build/upload failed for application_id=%s",
            application_id,
        )
        return {"final_pdf_url": None}

    return {"final_pdf_url": storage_path}


__all__ = [
    "application_builder_node",
    "build_context",
    "pdf_storage_path",
    "render_html",
    "render_pdf_bytes",
]
