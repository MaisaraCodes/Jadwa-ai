"""
DB-free / Storage-free tests for the self-healing PDF path
(core/application_builder.py: ensure_application_pdf + load_record_for_pdf).

This is the fix for the seeded-demo gap: applications backfilled straight to
review_ready never run the graph, so applications.final_pdf_url stays null even
though the analysis exists in agent_results. GET /pdf now builds on demand and
caches — these tests pin that contract:

    build -> upload -> final_pdf_url write-back -> second call serves the cache.

Supabase reads are faked (a tiny table->rows stub); render/upload/persist are
monkeypatched exactly like test_application_builder does, so no native
WeasyPrint stack is needed anywhere in this module.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core import application_builder as builder_mod
from core.application_builder import (
    ensure_application_pdf,
    load_record_for_pdf,
    pdf_storage_path,
)
from models import ApplicationRecord

# Reuse the canonical record/profile factories rather than redefining shapes
# (CONVENTIONS.md rule 7 in spirit — one source of fixture truth per shape).
from test_application_builder import APP_ID, make_financing, make_profile, make_record

EXPECTED_PATH = pdf_storage_path(APP_ID)


# --- fake Supabase reads -----------------------------------------------------
class _FakeQuery:
    """Just enough of the postgrest chain: select().eq().limit().execute()."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeSvc:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = tables

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._tables.get(name, []))


def app_row(**overrides) -> dict:
    row = {
        "id": APP_ID,
        "status": "review_ready",
        "final_pdf_url": None,
        "sme_profile_id": "sme-1",
        "amount": 350_000.0,
        "purpose": "توسيع تشكيلة قطع الغيار وتمويل رأس المال العامل",
        "term_months": 48,
        "description": None,
    }
    row.update(overrides)
    return row


@pytest.fixture
def pipeline(monkeypatch):
    """Fake the build pipeline around ensure_application_pdf: real record
    loading is stubbed per-test via `records`, rendering is a marker byte
    string, and upload/persist are captured instead of hitting Storage/DB."""
    calls = {"renders": 0, "uploads": [], "persisted": []}

    def fake_render(record):
        calls["renders"] += 1
        return b"%PDF-fake"

    def fake_upload(application_id, pdf_bytes):
        path = pdf_storage_path(application_id)
        calls["uploads"].append((path, pdf_bytes))
        return path

    monkeypatch.setattr(builder_mod, "render_pdf_bytes", fake_render)
    monkeypatch.setattr(builder_mod, "upload_pdf", fake_upload)
    monkeypatch.setattr(
        builder_mod,
        "persist_pdf_path",
        lambda app_id, path: calls["persisted"].append((app_id, path)),
    )
    return calls


def use_svc(monkeypatch, tables: dict[str, list[dict]]) -> None:
    monkeypatch.setattr(builder_mod, "get_service_client", lambda: _FakeSvc(tables))


# --- ensure_application_pdf --------------------------------------------------
class TestEnsureApplicationPdf:
    def test_builds_uploads_and_persists_when_final_pdf_url_is_null(
        self, monkeypatch, pipeline
    ):
        """The seeded-demo case: review_ready, analysis stored, no PDF."""
        use_svc(monkeypatch, {"applications": [app_row()]})
        monkeypatch.setattr(
            builder_mod, "load_record_for_pdf", lambda app_id, row: make_record()
        )

        path = ensure_application_pdf(APP_ID)

        assert path == EXPECTED_PATH
        assert pipeline["renders"] == 1
        assert pipeline["uploads"] == [(EXPECTED_PATH, b"%PDF-fake")]
        assert pipeline["persisted"] == [(APP_ID, EXPECTED_PATH)]

    def test_second_call_serves_the_cache_without_rebuilding(
        self, monkeypatch, pipeline
    ):
        """After the write-back, a stored path + live Storage object short-
        circuits everything — no render, no upload, no second UPDATE."""
        use_svc(
            monkeypatch,
            {"applications": [app_row(final_pdf_url=EXPECTED_PATH)]},
        )
        monkeypatch.setattr(builder_mod, "pdf_object_exists", lambda app_id: True)

        assert ensure_application_pdf(APP_ID) == EXPECTED_PATH
        assert pipeline["renders"] == 0
        assert pipeline["uploads"] == []
        assert pipeline["persisted"] == []

    def test_dangling_final_pdf_url_triggers_a_rebuild(self, monkeypatch, pipeline):
        """A stored path whose Storage object is gone (bucket wipe / re-seed)
        must not be signed into a 404 — rebuild instead."""
        use_svc(
            monkeypatch,
            {"applications": [app_row(final_pdf_url=EXPECTED_PATH)]},
        )
        monkeypatch.setattr(builder_mod, "pdf_object_exists", lambda app_id: False)
        monkeypatch.setattr(
            builder_mod, "load_record_for_pdf", lambda app_id, row: make_record()
        )

        assert ensure_application_pdf(APP_ID) == EXPECTED_PATH
        assert pipeline["renders"] == 1
        assert pipeline["persisted"] == [(APP_ID, EXPECTED_PATH)]

    @pytest.mark.parametrize("status", ["draft", "processing"])
    def test_non_terminal_status_is_not_built_on_demand(
        self, monkeypatch, pipeline, status
    ):
        """A mid-processing build would cache a half-empty report; the graph's
        own terminal builder node owns the happy path."""
        use_svc(monkeypatch, {"applications": [app_row(status=status)]})

        assert ensure_application_pdf(APP_ID) is None
        assert pipeline["renders"] == 0

    def test_unknown_application_returns_none(self, monkeypatch, pipeline):
        use_svc(monkeypatch, {"applications": []})
        assert ensure_application_pdf(APP_ID) is None

    def test_no_agent_output_returns_none_instead_of_an_empty_report(
        self, monkeypatch, pipeline
    ):
        use_svc(monkeypatch, {"applications": [app_row()]})
        monkeypatch.setattr(
            builder_mod, "load_record_for_pdf", lambda app_id, row: None
        )
        assert ensure_application_pdf(APP_ID) is None
        assert pipeline["renders"] == 0

    def test_build_failure_raises_instead_of_degrading_to_none(
        self, monkeypatch, pipeline
    ):
        """The API path must surface a real error (500 pdf_build_failed), never
        the permanent silent 'not generated yet' this bug shipped with."""
        use_svc(monkeypatch, {"applications": [app_row()]})
        monkeypatch.setattr(
            builder_mod, "load_record_for_pdf", lambda app_id, row: make_record()
        )

        def boom(*_a, **_k):
            raise RuntimeError("storage is down")

        monkeypatch.setattr(builder_mod, "upload_pdf", boom)
        with pytest.raises(RuntimeError):
            ensure_application_pdf(APP_ID)


# --- load_record_for_pdf -----------------------------------------------------
class TestLoadRecordForPdf:
    def test_prefers_the_stored_aggregate_and_backfills_financing(
        self, monkeypatch
    ):
        """Stored records written before ApplicationRecord.financing existed
        must still report the amount — it comes from the applications row."""
        stored = make_record(financing=None).model_dump(mode="json")
        use_svc(
            monkeypatch,
            {"agent_results": [{"application_id": APP_ID, "unified_application_record": stored}]},
        )

        record = load_record_for_pdf(APP_ID, app_row())
        assert isinstance(record, ApplicationRecord)
        assert record.financing is not None
        assert record.financing.amount == 350_000.0
        assert record.financing.term_months == 48

    def test_stored_financing_wins_over_the_applications_row(self, monkeypatch):
        stored = make_record().model_dump(mode="json")  # financing already set
        use_svc(
            monkeypatch,
            {"agent_results": [{"application_id": APP_ID, "unified_application_record": stored}]},
        )
        record = load_record_for_pdf(APP_ID, app_row(amount=999_999.0))
        assert record.financing.amount == make_financing().amount

    def test_assembles_from_individual_columns_when_aggregate_is_absent(
        self, monkeypatch
    ):
        source = make_record()
        agent_row = {
            "application_id": APP_ID,
            "unified_application_record": None,
            "extracted_documents": [
                d.model_dump(mode="json") for d in source.extracted_documents
            ],
            "forensic_report": source.forensic_report.model_dump(mode="json"),
            "weakness_report": source.weakness_report.model_dump(mode="json"),
            "market_verdict": source.market_verdict.model_dump(mode="json"),
            "risk_baseline": source.risk_baseline.model_dump(mode="json"),
        }
        profile_row = make_profile().model_dump(mode="json")
        use_svc(
            monkeypatch,
            {"agent_results": [agent_row], "sme_profiles": [profile_row]},
        )

        record = load_record_for_pdf(APP_ID, app_row())
        assert record.forensic_report == source.forensic_report
        assert record.weakness_report == source.weakness_report
        assert record.market_verdict == source.market_verdict
        assert record.risk_baseline == source.risk_baseline
        assert record.extracted_documents == source.extracted_documents
        assert record.status == "review_ready"
        assert record.financing.amount == 350_000.0

    def test_returns_none_when_no_agent_output_exists(self, monkeypatch):
        use_svc(monkeypatch, {"agent_results": []})
        assert load_record_for_pdf(APP_ID, app_row()) is None

    def test_returns_none_when_agent_row_is_empty(self, monkeypatch):
        use_svc(
            monkeypatch,
            {"agent_results": [{"application_id": APP_ID}], "sme_profiles": []},
        )
        assert load_record_for_pdf(APP_ID, app_row()) is None
