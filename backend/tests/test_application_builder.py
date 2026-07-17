"""
DB-free / Storage-free tests for application_builder_node
(core/application_builder.py) — the Arabic PDF builder (architecture.md §1).

Storage and the applications UPDATE are monkeypatched: the tests assert what
WOULD have been uploaded (bucket, path, content type, bytes) rather than
uploading it. No LLM is involved in this node by design.

These tests DO render real PDFs, so they need WeasyPrint's native Pango/GTK
stack — see requirements.txt. Where that's absent (a stock Windows box), the
render tests skip rather than fail; the wiring and None-handling tests still
run, since neither touches WeasyPrint.
"""
from __future__ import annotations

from datetime import date

import pytest

from core import application_builder as builder_mod
from core.application_builder import (
    application_builder_node,
    build_context,
    pdf_storage_path,
    render_html,
    render_pdf_bytes,
)
from models import (
    ApplicationRecord,
    ApplicationState,
    DiscrepancyFlag,
    DocumentJSON,
    ForensicReport,
    MarketVerdict,
    RiskBaseline,
    SMEProfile,
    WeaknessReport,
)

APP_ID = "app-123"

# Skips the render tests (not the whole module) when the native stack is absent,
# so the wiring/None coverage still runs everywhere.
try:  # pragma: no cover - environment probe
    import weasyprint  # noqa: F401

    WEASYPRINT_AVAILABLE = True
except Exception:  # pragma: no cover
    WEASYPRINT_AVAILABLE = False

needs_weasyprint = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint's native Pango/GTK libraries are not installed here",
)


def _open(pdf: bytes):
    """Parse rendered bytes for inspection. pymupdf (already in requirements.txt
    for the vision pipeline) reads the compressed object streams that hold the
    metadata and font names — a regex over the raw bytes cannot."""
    import fitz

    return fitz.open(stream=pdf, filetype="pdf")


# --- fixtures ----------------------------------------------------------------
def make_profile() -> SMEProfile:
    return SMEProfile(
        id="sme-1",
        company_name="مستودع الخليج للوقود",
        cr_number="1010101010",
        sector="الخدمات اللوجستية",
        district="الخرج",
        established_year=2019,
    )


def make_document(doc_id: str = "doc-1", day: int = 12) -> DocumentJSON:
    return DocumentJSON(
        document_id=doc_id,
        type="zatca_receipt",
        vendor="Desert Traders",
        extracted_amount=1500.50,
        date=date(2025, 10, day),
        confidence_score=0.98,
    )


def make_record(**overrides) -> ApplicationRecord:
    fields = {
        "application_id": APP_ID,
        "status": "processing",
        "sme_profile": make_profile(),
        "extracted_documents": [make_document()],
        "forensic_report": ForensicReport(
            overall_status="yellow",
            reconciliation_rate=0.85,
            discrepancy_flags=[
                DiscrepancyFlag(severity="high", description="مبلغ الإيصال لا يطابق السجل."),
                DiscrepancyFlag(severity="medium", description="فاتورة بدون رمز QR مطابق."),
            ],
        ),
        "weakness_report": WeaknessReport(
            critical_weaknesses=["اعتماد مرتفع على مورّد واحد."],
            mitigation_suggestions=["طلب إثبات عقود موردين ثانويين."],
            business_model_score=72,
        ),
        "market_verdict": MarketVerdict(
            sector_trend="growing",
            district_saturation="medium",
            oracle_insight="نمو سنوي بنسبة 14% في قطاع الخدمات اللوجستية.",
            sources_cited=["SAMA SME Report Q3 2025"],
        ),
        "risk_baseline": RiskBaseline(
            base_default_probability=0.12,
            revenue_volatility_multiplier=1.05,
            cash_buffer_months=3.2,
            recommended_interest_rate=0.08,
        ),
    }
    fields.update(overrides)
    return ApplicationRecord(**fields)


def make_state(**overrides) -> ApplicationState:
    state: ApplicationState = {
        "application_id": APP_ID,
        "status": "processing",
        "sme_profile": make_profile(),
        "raw_documents": [],
        "extracted_documents": [make_document()],
        "forensic_report": None,
        "weakness_report": None,
        "market_verdict": None,
        "risk_baseline": None,
        "unified_application_record": make_record(),
        "final_pdf_url": None,
    }
    state.update(overrides)
    return state


@pytest.fixture
def storage(monkeypatch):
    """Storage-free + DB-free: capture the upload and the applications UPDATE."""
    uploads: list[dict] = []
    persisted: list[tuple[str, str]] = []

    def fake_upload(application_id: str, pdf_bytes: bytes) -> str:
        path = pdf_storage_path(application_id)
        uploads.append(
            {
                "bucket": builder_mod.PDF_BUCKET,
                "path": path,
                "bytes": pdf_bytes,
                "content_type": builder_mod.PDF_CONTENT_TYPE,
            }
        )
        return path

    monkeypatch.setattr(builder_mod, "upload_pdf", fake_upload)
    monkeypatch.setattr(
        builder_mod, "persist_pdf_path", lambda app_id, path: persisted.append((app_id, path))
    )
    return {"uploads": uploads, "persisted": persisted}


# --- happy path --------------------------------------------------------------
class TestRenderHappyPath:
    @needs_weasyprint
    def test_full_record_produces_a_valid_non_empty_pdf(self):
        pdf = render_pdf_bytes(make_record())
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 1000

    @needs_weasyprint
    def test_bundled_arabic_fonts_are_embedded(self):
        """A missing font file wouldn't raise — WeasyPrint would silently fall
        back to a system face and quietly ruin the Arabic. Assert the bundled
        faces actually made it into the PDF.

        Read via pymupdf, not a regex over the raw bytes: the font names live in
        compressed object streams, so a raw-bytes search reports "not embedded"
        for a PDF whose fonts are perfectly fine.
        """
        doc = _open(render_pdf_bytes(make_record()))
        names = " ".join(f[3] for page in doc for f in page.get_fonts())
        assert "Zain" in names, f"Zain (display) not embedded: {names}"
        assert "Alexandria" in names, f"Alexandria (body) not embedded: {names}"

    @needs_weasyprint
    def test_alexandria_variable_axis_yields_all_three_body_weights(self):
        """Alexandria is a variable font and the @font-face deliberately carries
        no font-weight descriptor (see the template). Adding one collapses every
        label to weight 400 — the PDF still renders, so only the embedded subset
        list catches it. This is that check."""
        doc = _open(render_pdf_bytes(make_record()))
        names = " ".join(f[3] for page in doc for f in page.get_fonts())
        assert "Alexandria-Medium" in names, f"weight 500 lost: {names}"
        assert "Alexandria-Semi-Bold" in names, f"weight 600 lost: {names}"

    def test_html_contains_every_section_in_order(self):
        html = render_html(make_record())
        headings = [
            "بيانات المنشأة",          # a. SME profile
            "ملخص التدقيق المحاسبي",   # b. forensic
            "تقرير نقاط الضعف",        # c. weakness
            "جدوى السوق",              # d. market
            "المؤشرات المالية",        # e. financial
        ]
        positions = [html.index(h) for h in headings]
        assert positions == sorted(positions), "sections are out of order"

    def test_html_carries_the_record_values(self):
        html = render_html(make_record())
        assert "مستودع الخليج للوقود" in html
        assert "1010101010" in html
        assert "85.0%" in html          # reconciliation_rate
        assert "72" in html             # business_model_score
        assert "12.0%" in html          # base_default_probability
        assert "دراسة جدوى تمويل" in html  # cover subtitle

    def test_forensic_status_maps_to_the_design_system_token(self):
        for status, token in (("green", "pass"), ("yellow", "review"), ("red", "flag")):
            record = make_record(
                forensic_report=ForensicReport(
                    overall_status=status, reconciliation_rate=1.0, discrepancy_flags=[]
                )
            )
            assert build_context(record)["forensic_status_token"] == token

    def test_sandbox_projection_is_not_in_the_pdf(self):
        """Scope call: the 12-month projection is an interactive tool
        (architecture.md §3), not a static artifact."""
        html = render_html(make_record())
        assert "cash_flow" not in html
        assert "risk_score" not in html


# --- None handling -----------------------------------------------------------
class TestPartialRecord:
    @pytest.mark.parametrize(
        "missing", ["forensic_report", "weakness_report", "market_verdict", "risk_baseline"]
    )
    def test_single_missing_section_renders_the_arabic_placeholder(self, missing):
        html = render_html(make_record(**{missing: None}))
        assert builder_mod.NOT_AVAILABLE in html

    @needs_weasyprint
    def test_everything_none_except_profile_still_produces_a_valid_pdf(self):
        record = ApplicationRecord(
            application_id=APP_ID, status="processing", sme_profile=make_profile()
        )
        pdf = render_pdf_bytes(record)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 1000

    def test_everything_none_shows_the_placeholder_for_all_four_sections(self):
        record = ApplicationRecord(
            application_id=APP_ID, status="processing", sme_profile=make_profile()
        )
        html = render_html(record)
        assert html.count(builder_mod.NOT_AVAILABLE) == 4

    def test_empty_flag_and_source_lists_do_not_crash(self):
        record = make_record(
            forensic_report=ForensicReport(
                overall_status="green", reconciliation_rate=1.0, discrepancy_flags=[]
            ),
            weakness_report=WeaknessReport(
                critical_weaknesses=[], mitigation_suggestions=[], business_model_score=0
            ),
            market_verdict=MarketVerdict(
                sector_trend="stable",
                district_saturation="low",
                oracle_insight="",
                sources_cited=[],
            ),
        )
        assert "بيانات المنشأة" in render_html(record)

    def test_no_documents_omits_the_cover_date_rather_than_inventing_one(self):
        record = make_record(extracted_documents=[])
        assert build_context(record)["cover_date"] is None
        assert "أحدث مستند بتاريخ" not in render_html(record)

    def test_missing_established_year_renders_an_em_dash(self):
        profile = make_profile()
        profile.established_year = None
        assert "—" in render_html(make_record(sme_profile=profile))


# --- determinism -------------------------------------------------------------
class TestDeterminism:
    @needs_weasyprint
    def test_identical_record_renders_identical_bytes(self):
        """Requirement 10: the demo must be repeatable.

        Two leaks had to be plugged for this to hold — the PDF /CreationDate
        (fixed via the template's dcterms.created meta) and fontTools stamping
        head.modified into the embedded font subsets (fixed via
        SOURCE_DATE_EPOCH in core/application_builder). Nothing is stripped
        post-hoc: the bytes are equal end to end.
        """
        record = make_record()
        assert render_pdf_bytes(record) == render_pdf_bytes(record)

    @needs_weasyprint
    def test_rebuilding_the_record_from_json_renders_identical_bytes(self):
        """Same data through a persist/reload round-trip → same PDF."""
        record = make_record()
        reloaded = ApplicationRecord.model_validate(record.model_dump(mode="json"))
        assert render_pdf_bytes(record) == render_pdf_bytes(reloaded)

    @needs_weasyprint
    def test_different_records_render_different_bytes(self):
        """Guards the determinism assertions above from passing trivially."""
        a = render_pdf_bytes(make_record())
        b = render_pdf_bytes(make_record(weakness_report=WeaknessReport(
            critical_weaknesses=["مختلف"], mitigation_suggestions=[], business_model_score=10
        )))
        assert a != b

    @needs_weasyprint
    def test_pdf_metadata_dates_are_pinned_not_wall_clock(self):
        """/CreationDate and /ModDate come from the template's dcterms meta.
        Read via pymupdf — they sit in a compressed object stream, invisible to
        a raw-bytes search."""
        meta = _open(render_pdf_bytes(make_record())).metadata
        assert meta["creationDate"].startswith("D:20250101")
        assert meta["modDate"].startswith("D:20250101")
        assert str(date.today().year) not in meta["creationDate"]

    def test_cover_date_comes_from_the_newest_document_not_today(self):
        record = make_record(
            extracted_documents=[make_document("d1", day=12), make_document("d2", day=27)]
        )
        assert build_context(record)["cover_date"] == date(2025, 10, 27)


# --- the node ----------------------------------------------------------------
class TestNode:
    @needs_weasyprint
    def test_writes_only_final_pdf_url(self, storage):
        out = application_builder_node(make_state())
        assert set(out.keys()) == {"final_pdf_url"}

    @needs_weasyprint
    def test_uploads_to_the_expected_bucket_and_path(self, storage):
        application_builder_node(make_state())
        assert len(storage["uploads"]) == 1
        upload = storage["uploads"][0]
        assert upload["bucket"] == "application-documents"
        assert upload["path"] == f"{APP_ID}/report.pdf"
        assert upload["content_type"] == "application/pdf"
        assert upload["bytes"][:5] == b"%PDF-"

    @needs_weasyprint
    def test_returns_and_persists_the_same_storage_path(self, storage):
        out = application_builder_node(make_state())
        assert out["final_pdf_url"] == f"{APP_ID}/report.pdf"
        assert storage["persisted"] == [(APP_ID, f"{APP_ID}/report.pdf")]

    @needs_weasyprint
    def test_does_not_mutate_other_state_keys(self, storage):
        state = make_state()
        before = {k: state[k] for k in state}
        application_builder_node(state)
        for key in before:
            assert state[key] == before[key], f"state key {key!r} was mutated"

    def test_missing_unified_record_returns_none_without_raising(self, storage):
        out = application_builder_node(make_state(unified_application_record=None))
        assert out == {"final_pdf_url": None}
        assert storage["uploads"] == []

    def test_storage_failure_degrades_to_none_instead_of_failing_the_graph(
        self, storage, monkeypatch
    ):
        """The PDF is a derived artifact — the unified record is already
        persisted by aggregate_results_node. A Storage outage must not lose the
        analysis that actually matters."""
        def boom(*_args, **_kwargs):
            raise RuntimeError("storage is down")

        monkeypatch.setattr(builder_mod, "render_pdf_bytes", lambda record: b"%PDF-fake")
        monkeypatch.setattr(builder_mod, "upload_pdf", boom)
        assert application_builder_node(make_state()) == {"final_pdf_url": None}

    def test_node_does_not_touch_the_lifecycle_status(self, storage, monkeypatch):
        """`submitted` is not a valid DB enum value (architecture.md §4), and
        processing → review_ready is owned by core/orchestrator.py after the
        whole graph completes. This node must not advance the lifecycle."""
        monkeypatch.setattr(builder_mod, "render_pdf_bytes", lambda record: b"%PDF-fake")
        out = application_builder_node(make_state())
        assert "status" not in out


# --- graph wiring ------------------------------------------------------------
class TestGraphWiring:
    def test_aggregate_edges_to_the_builder_and_not_to_end(self):
        from langgraph.graph import END

        from core.graph import build_graph

        edges = build_graph().get_graph().edges
        outgoing = {e.target for e in edges if e.source == "aggregate_results_node"}
        assert outgoing == {"application_builder_node"}
        assert END not in outgoing

    def test_builder_is_the_terminal_node(self):
        from langgraph.graph import END

        from core.graph import build_graph

        edges = build_graph().get_graph().edges
        outgoing = {e.target for e in edges if e.source == "application_builder_node"}
        assert outgoing == {END}

    def test_builder_runs_after_all_four_agents(self):
        """The builder must not be reachable before the aggregate join."""
        from core.graph import build_graph

        edges = build_graph().get_graph().edges
        incoming = {e.source for e in edges if e.target == "application_builder_node"}
        assert incoming == {"aggregate_results_node"}
