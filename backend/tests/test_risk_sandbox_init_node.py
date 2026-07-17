"""
DB-free / LLM-free tests for risk_sandbox_init_node (core/graph.py) — the
pure-Python RiskBaseline precompute (architecture.md §3, schema_mapping.md §2
Node 5). Mirrors tests/test_aggregate_results_node.py: `_persist_column` is
monkeypatched so no Supabase client is touched, and no LLM is involved by design.
"""
from __future__ import annotations

import copy
from datetime import date

import pytest

from core import graph as graph_mod
from core.graph import risk_sandbox_init_node
from models import ApplicationState, DocumentJSON, RiskBaseline, SMEProfile

APP_ID = "app-123"


def make_profile() -> SMEProfile:
    return SMEProfile(
        id="sme-1",
        company_name="Rawad Logistics",
        cr_number="1010482913",
        sector="logistics",
        district="Al-Kharj",
    )


def make_document(doc_id: str, amount: float) -> DocumentJSON:
    return DocumentJSON(
        document_id=doc_id,
        type="invoice",
        vendor="ADNOC Fuel",
        extracted_amount=amount,
        date=date(2025, 10, 12),
        confidence_score=0.98,
    )


def make_state(documents, **overrides) -> ApplicationState:
    state: ApplicationState = {
        "application_id": APP_ID,
        "status": "processing",
        "sme_profile": make_profile(),
        "raw_documents": [],
        "extracted_documents": documents,
        "forensic_report": None,
        "weakness_report": None,
        "market_verdict": None,
        "risk_baseline": None,
        "unified_application_record": None,
    }
    state.update(overrides)
    return state


# 5 realistic invoice amounts spanning the seeded band (~1.2k-18k).
RICH_DOCS = [
    make_document("doc-1", 1_500.50),
    make_document("doc-2", 6_200.00),
    make_document("doc-3", 9_800.75),
    make_document("doc-4", 3_400.00),
    make_document("doc-5", 14_250.25),
]


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    """DB-free: capture persistence calls instead of hitting Supabase."""
    calls: list[tuple] = []
    monkeypatch.setattr(
        graph_mod, "_persist_column", lambda app_id, column, value: calls.append((app_id, column, value))
    )
    yield calls


class TestEmptyDocs:
    def test_empty_list_returns_neutral_defaults(self, no_db):
        out = risk_sandbox_init_node(make_state([]))
        baseline = out["risk_baseline"]
        assert isinstance(baseline, RiskBaseline)
        assert baseline.base_default_probability == 0.10
        assert baseline.revenue_volatility_multiplier == 1.0
        assert baseline.cash_buffer_months == 3.0
        assert baseline.recommended_interest_rate == 0.08

    def test_missing_key_does_not_throw(self, no_db):
        state = make_state([])
        del state["extracted_documents"]  # key absent entirely
        out = risk_sandbox_init_node(state)  # must not raise
        assert isinstance(out["risk_baseline"], RiskBaseline)

    def test_none_docs_does_not_throw(self, no_db):
        out = risk_sandbox_init_node(make_state(None))
        assert out["risk_baseline"].base_default_probability == 0.10


class TestRichDocs:
    def test_all_fields_within_realistic_ranges(self, no_db):
        out = risk_sandbox_init_node(make_state(RICH_DOCS))
        baseline = out["risk_baseline"]
        # Re-validate through the model (JSON round-trip like every other node).
        restored = RiskBaseline.model_validate(baseline.model_dump(mode="json"))
        assert restored == baseline

        assert 0.0 <= baseline.base_default_probability <= 1.0
        assert 0.8 <= baseline.revenue_volatility_multiplier <= 1.4
        assert 1.0 <= baseline.cash_buffer_months <= 6.0
        assert 0.05 <= baseline.recommended_interest_rate <= 0.12

    def test_healthy_file_lands_at_anchor_probability(self, no_db):
        # 5 docs, total > 10k -> neither thin-file nor low-total penalty applies.
        baseline = risk_sandbox_init_node(make_state(RICH_DOCS))["risk_baseline"]
        assert baseline.base_default_probability == 0.10

    def test_thin_low_file_nudges_probability_up(self, no_db):
        # 2 docs (< 3) AND tiny total (< 10k) -> both penalties stack.
        docs = [make_document("d1", 500.0), make_document("d2", 800.0)]
        baseline = risk_sandbox_init_node(make_state(docs))["risk_baseline"]
        assert baseline.base_default_probability == pytest.approx(0.20)


class TestDeterminism:
    def test_same_input_same_output_three_runs(self, no_db):
        results = [
            risk_sandbox_init_node(make_state(RICH_DOCS))["risk_baseline"].model_dump()
            for _ in range(3)
        ]
        assert results[0] == results[1] == results[2]


class TestStateIsolation:
    def test_writes_only_risk_baseline_key(self, no_db):
        out = risk_sandbox_init_node(make_state(RICH_DOCS))
        assert set(out.keys()) == {"risk_baseline"}

    def test_does_not_mutate_other_state_keys(self, no_db):
        state = make_state(RICH_DOCS)
        before = copy.deepcopy(state)
        risk_sandbox_init_node(state)
        for key in before:
            assert state[key] == before[key], f"state key {key!r} was mutated"


class TestPersistence:
    def test_persists_to_risk_baseline_column(self, no_db):
        baseline = risk_sandbox_init_node(make_state(RICH_DOCS))["risk_baseline"]
        assert no_db == [(APP_ID, "risk_baseline", baseline.model_dump(mode="json"))]
