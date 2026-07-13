"""
Pure-Python tests for the Devil's Advocate signal layer
(nodes/devils_advocate/signals.py) and scoring layer
(nodes/devils_advocate/scoring.py). No DB, no LLM.
"""
from __future__ import annotations

from datetime import date

import pytest

from models import DocumentJSON
from nodes.devils_advocate.scoring import business_model_score, rank_weaknesses
from nodes.devils_advocate.signals import (
    SignalResult,
    compute_all_signals,
    compute_client_concentration,
    compute_revenue_volatility,
    compute_sector_cost_exposure,
    compute_vendor_concentration,
)


def debit_row(amount: float, when: str, counterparty: str) -> dict:
    return {
        "transaction_date": when, "amount": -amount,
        "description": f"Recurring cost — {counterparty}", "transaction_type": "debit",
    }


def credit_row(amount: float, when: str, counterparty: str = "Customer receipts") -> dict:
    return {
        "transaction_date": when, "amount": amount,
        "description": f"Monthly revenue — {counterparty}", "transaction_type": "credit",
    }


def make_doc(vendor: str, amount: float) -> DocumentJSON:
    return DocumentJSON(
        document_id="doc", type="invoice", vendor=vendor,
        extracted_amount=amount, date=date(2025, 1, 1), confidence_score=0.9,
    )


# ---------------------------------------------------------------------------
# vendor_concentration
# ---------------------------------------------------------------------------
class TestVendorConcentration:
    def test_below_medium_is_not_triggered(self):
        rows = [
            debit_row(100, "2025-01-01", "A"),
            debit_row(100, "2025-02-01", "B"),
            debit_row(100, "2025-03-01", "C"),
        ]
        result = compute_vendor_concentration(rows)
        assert result.assessable
        assert not result.triggered
        assert result.severity is None

    def test_just_above_medium_threshold_is_medium(self):
        rows = [debit_row(61, "2025-01-01", "A"), debit_row(39, "2025-02-01", "B")]
        result = compute_vendor_concentration(rows)
        assert result.triggered
        assert result.severity == "medium"
        assert result.metric == pytest.approx(0.61)

    def test_just_above_high_threshold_is_high(self):
        rows = [debit_row(76, "2025-01-01", "A"), debit_row(24, "2025-02-01", "B")]
        result = compute_vendor_concentration(rows)
        assert result.triggered
        assert result.severity == "high"

    def test_exactly_at_medium_threshold_is_not_triggered(self):
        # Strictly-greater-than semantics: exactly 0.60 must not trigger.
        rows = [debit_row(60, "2025-01-01", "A"), debit_row(40, "2025-02-01", "B")]
        result = compute_vendor_concentration(rows)
        assert not result.triggered

    def test_too_few_rows_is_not_assessable(self):
        result = compute_vendor_concentration([debit_row(100, "2025-01-01", "A")])
        assert not result.assessable
        assert not result.triggered

    def test_empty_is_not_assessable(self):
        assert not compute_vendor_concentration([]).assessable


# ---------------------------------------------------------------------------
# client_concentration
# ---------------------------------------------------------------------------
class TestClientConcentration:
    def test_single_shared_counterparty_is_not_assessable(self):
        # Mirrors the real mock_open_banking_ledger: every credit row is
        # "Customer receipts" — no per-client breakdown exists (STEP 0).
        rows = [credit_row(100_000, "2025-01-03"), credit_row(120_000, "2025-02-03")]
        result = compute_client_concentration(rows)
        assert not result.assessable
        assert not result.triggered

    def test_real_per_client_breakdown_is_assessable(self):
        rows = [
            credit_row(80_000, "2025-01-03", "Client A"),
            credit_row(20_000, "2025-01-15", "Client B"),
        ]
        result = compute_client_concentration(rows)
        assert result.assessable
        assert result.triggered
        assert result.severity == "high"

    def test_too_few_rows_is_not_assessable(self):
        assert not compute_client_concentration([credit_row(100, "2025-01-01")]).assessable

    def test_empty_is_not_assessable(self):
        assert not compute_client_concentration([]).assessable


# ---------------------------------------------------------------------------
# revenue_volatility
# ---------------------------------------------------------------------------
class TestRevenueVolatility:
    def test_stable_revenue_is_not_triggered(self):
        rows = [credit_row(100_000, f"2025-{m:02d}-03") for m in range(1, 7)]
        result = compute_revenue_volatility(rows)
        assert result.assessable
        assert not result.triggered
        assert result.metric == pytest.approx(0.0)

    def test_volatile_revenue_triggers(self):
        amounts = [50_000, 200_000, 40_000, 220_000, 60_000, 210_000]
        rows = [credit_row(a, f"2025-{m:02d}-03") for m, a in enumerate(amounts, start=1)]
        result = compute_revenue_volatility(rows)
        assert result.triggered
        assert result.severity in {"medium", "high"}

    def test_multiple_rows_in_one_month_are_summed_not_double_counted(self):
        rows = [
            credit_row(50_000, "2025-01-03"), credit_row(50_000, "2025-01-20"),
            credit_row(100_000, "2025-02-03"),
        ]
        result = compute_revenue_volatility(rows)
        # Both months net to 100,000 -> zero volatility, not a spurious spike.
        assert result.metric == pytest.approx(0.0)

    def test_too_few_months_is_not_assessable(self):
        assert not compute_revenue_volatility([credit_row(100_000, "2025-01-03")]).assessable

    def test_empty_is_not_assessable(self):
        assert not compute_revenue_volatility([]).assessable


# ---------------------------------------------------------------------------
# sector_cost_exposure
# ---------------------------------------------------------------------------
class TestSectorCostExposure:
    def test_fuel_heavy_logistics_business_triggers(self):
        docs = [make_doc("ADNOC Fuel", 8_000), make_doc("Almarai", 2_000)]
        result = compute_sector_cost_exposure(docs, "logistics")
        assert result.assessable
        assert result.triggered
        assert result.severity == "medium"

    def test_diversified_spend_does_not_trigger(self):
        docs = [make_doc("Jarir", 3_000), make_doc("Almarai", 3_000), make_doc("STC Business", 3_000)]
        result = compute_sector_cost_exposure(docs, "logistics")
        assert not result.triggered

    def test_unknown_sector_is_not_assessable(self):
        docs = [make_doc("ADNOC Fuel", 8_000)]
        result = compute_sector_cost_exposure(docs, "unknown_sector")
        assert not result.assessable

    def test_no_documents_is_not_assessable(self):
        assert not compute_sector_cost_exposure([], "logistics").assessable

    def test_none_sector_does_not_crash(self):
        assert not compute_sector_cost_exposure([make_doc("ADNOC Fuel", 100)], None).assessable


# ---------------------------------------------------------------------------
# compute_all_signals — empty-data safety
# ---------------------------------------------------------------------------
class TestComputeAllSignals:
    def test_empty_everything_is_all_not_assessable_no_crash(self):
        signals = compute_all_signals(debit_rows=[], credit_rows=[], documents=[], sector="logistics")
        assert len(signals) == 4
        assert all(not s.triggered for s in signals)


# ---------------------------------------------------------------------------
# business_model_score — math + clamping
# ---------------------------------------------------------------------------
class TestBusinessModelScore:
    def test_no_triggered_signals_is_100(self):
        signals = [SignalResult("s", True, 0.1, False, None, 0)]
        assert business_model_score(signals) == 100

    def test_penalties_subtract(self):
        signals = [
            SignalResult("a", True, 0.8, True, "high", 25),
            SignalResult("b", True, 0.4, True, "medium", 10),
        ]
        assert business_model_score(signals) == 65

    def test_clamped_at_zero(self):
        signals = [SignalResult(f"s{i}", True, 1.0, True, "high", 25) for i in range(5)]
        assert business_model_score(signals) == 0

    def test_empty_signals_is_100(self):
        assert business_model_score([]) == 100


# ---------------------------------------------------------------------------
# rank_weaknesses — ranking + limit
# ---------------------------------------------------------------------------
class TestRankWeaknesses:
    def test_only_triggered_signals_are_ranked(self):
        signals = [
            SignalResult("a", True, 0.1, False, None, 0),
            SignalResult("b", True, 0.8, True, "high", 25),
        ]
        assert rank_weaknesses(signals) == [signals[1]]

    def test_ranked_by_penalty_descending(self):
        signals = [
            SignalResult("a", True, 0.6, True, "medium", 12),
            SignalResult("b", True, 0.8, True, "high", 25),
            SignalResult("c", True, 0.35, True, "medium", 10),
        ]
        ranked = rank_weaknesses(signals)
        assert [s.signal for s in ranked] == ["b", "a", "c"]

    def test_capped_at_limit(self):
        signals = [SignalResult(f"s{i}", True, 1.0, True, "high", 25) for i in range(4)]
        assert len(rank_weaknesses(signals, limit=2)) == 2

    def test_empty_signals_ranks_to_empty(self):
        assert rank_weaknesses([]) == []
