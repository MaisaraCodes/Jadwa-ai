"""
DB-free / LLM-free tests for aggregate_results_node (core/graph.py) — the
deterministic merge node (architecture.md §1, schema_mapping.md §2 Node 6).

Persistence is mocked (`_persist_column` monkeypatched), so no Supabase client
is touched. No LLM is involved anywhere in this node by design.
"""
from __future__ import annotations

import copy
from datetime import date

import pytest

from core import graph as graph_mod
from core.graph import aggregate_results_node
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


def make_profile() -> SMEProfile:
    return SMEProfile(
        id="sme-1",
        company_name="Gulf Fuel Depot",
        cr_number="1010101010",
        sector="logistics",
        district="Al-Kharj",
    )


def make_document(doc_id: str = "doc-1") -> DocumentJSON:
    return DocumentJSON(
        document_id=doc_id,
        type="zatca_receipt",
        vendor="Desert Traders",
        extracted_amount=1500.50,
        date=date(2025, 10, 12),
        confidence_score=0.98,
    )


def make_forensic() -> ForensicReport:
    return ForensicReport(
        overall_status="yellow",
        reconciliation_rate=0.85,
        discrepancy_flags=[DiscrepancyFlag(severity="medium", description="mismatch")],
    )


def make_weakness() -> WeaknessReport:
    return WeaknessReport(
        critical_weaknesses=["Single-vendor reliance"],
        mitigation_suggestions=["Secondary supplier contracts"],
        business_model_score=72,
    )


def make_verdict() -> MarketVerdict:
    return MarketVerdict(
        sector_trend="growing",
        district_saturation="medium",
        oracle_insight="Logistics in Al-Kharj shows 14% YoY growth.",
        sources_cited=["SAMA SME Report Q3 2025"],
    )


def make_baseline() -> RiskBaseline:
    return RiskBaseline(
        base_default_probability=0.12,
        revenue_volatility_multiplier=1.05,
        cash_buffer_months=3.2,
        recommended_interest_rate=0.08,
    )


def make_state(**overrides) -> ApplicationState:
    state: ApplicationState = {
        "application_id": APP_ID,
        "status": "processing",
        "sme_profile": make_profile(),
        "raw_documents": [],
        "extracted_documents": [make_document()],
        "forensic_report": make_forensic(),
        "weakness_report": make_weakness(),
        "market_verdict": make_verdict(),
        "risk_baseline": make_baseline(),
        "unified_application_record": None,
    }
    state.update(overrides)
    return state


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    """DB-free: capture persistence calls instead of hitting Supabase."""
    calls: list[tuple] = []
    monkeypatch.setattr(
        graph_mod, "_persist_column", lambda app_id, column, value: calls.append((app_id, column, value))
    )
    yield calls


class TestFullMerge:
    def test_all_four_outputs_present(self, no_db):
        state = make_state()
        out = aggregate_results_node(state)

        record = out["unified_application_record"]
        assert isinstance(record, ApplicationRecord)
        assert record.application_id == APP_ID
        assert record.status == "processing"
        assert record.sme_profile == make_profile()
        assert record.extracted_documents == [make_document()]
        assert record.forensic_report == make_forensic()
        assert record.weakness_report == make_weakness()
        assert record.market_verdict == make_verdict()
        assert record.risk_baseline == make_baseline()

    def test_writes_only_its_own_state_key(self, no_db):
        out = aggregate_results_node(make_state())
        assert set(out.keys()) == {"unified_application_record"}

    def test_does_not_mutate_other_state_keys(self, no_db):
        state = make_state()
        before = copy.deepcopy(state)
        aggregate_results_node(state)
        # every pre-existing key untouched
        for key in before:
            assert state[key] == before[key], f"state key {key!r} was mutated"

    def test_record_validates_and_round_trips_json(self, no_db):
        record = aggregate_results_node(make_state())["unified_application_record"]
        restored = ApplicationRecord.model_validate(record.model_dump(mode="json"))
        assert restored == record

    def test_persists_to_unified_application_record_column(self, no_db):
        record = aggregate_results_node(make_state())["unified_application_record"]
        assert no_db == [(APP_ID, "unified_application_record", record.model_dump(mode="json"))]


class TestPartialMerge:
    @pytest.mark.parametrize(
        "missing",
        ["forensic_report", "weakness_report", "market_verdict", "risk_baseline"],
    )
    def test_single_missing_output_passes_none_through(self, missing, no_db):
        state = make_state(**{missing: None})
        record = aggregate_results_node(state)["unified_application_record"]
        assert isinstance(record, ApplicationRecord)
        assert getattr(record, missing) is None
        # the other three are untouched — no fabricated defaults
        for key in ("forensic_report", "weakness_report", "market_verdict", "risk_baseline"):
            if key != missing:
                assert getattr(record, key) is not None

    def test_all_four_missing_still_validates(self, no_db):
        state = make_state(
            forensic_report=None,
            weakness_report=None,
            market_verdict=None,
            risk_baseline=None,
        )
        record = aggregate_results_node(state)["unified_application_record"]
        assert isinstance(record, ApplicationRecord)
        assert record.forensic_report is None
        assert record.weakness_report is None
        assert record.market_verdict is None
        assert record.risk_baseline is None
        # round-trips with Nones intact
        restored = ApplicationRecord.model_validate(record.model_dump(mode="json"))
        assert restored == record

    def test_missing_extracted_documents_defaults_to_empty_list(self, no_db):
        state = make_state()
        del state["extracted_documents"]
        record = aggregate_results_node(state)["unified_application_record"]
        assert record.extracted_documents == []


class TestStatusCarryThrough:
    @pytest.mark.parametrize("status", ["draft", "processing", "review_ready"])
    def test_status_carried_from_state_unchanged(self, status, no_db):
        record = aggregate_results_node(make_state(status=status))["unified_application_record"]
        assert record.status == status

    def test_missing_status_falls_back_to_processing(self, no_db):
        state = make_state()
        del state["status"]
        record = aggregate_results_node(state)["unified_application_record"]
        assert record.status == "processing"
