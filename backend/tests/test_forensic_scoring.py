"""
Pure-Python tests for the forensic scoring + roll-up layer
(nodes/forensic/scoring.py) and the deterministic description fallback
(nodes/forensic/explain.py). No LLM, no DB — fixtures mirror the three
invoice buckets in SYNTHETIC_DATA_SPEC.md: legitimate & reconciling,
fabricated, and genuine mismatch/noise.
"""
from __future__ import annotations

from datetime import date

import pytest

from models import ForensicReport
from nodes.forensic import explain
from nodes.forensic.explain import InvoiceContext, write_flag_descriptions
from nodes.forensic.scoring import (
    AMOUNT_TOLERANCE_SAR,
    DATE_WINDOW_DAYS,
    REPEATED_AMOUNT_MIN_COUNT,
    MatchResult,
    build_forensic_report,
    is_suspiciously_round,
    repeated_amount_document_ids,
    score_invoice,
)


def make_match(document_id: str = "doc-1", **overrides) -> MatchResult:
    defaults = dict(
        matched=True,
        ledger_txn_id="txn-1",
        amount_delta=0.0,
        date_delta_days=0,
        is_round_amount=False,
        is_repeated_amount=False,
    )
    defaults.update(overrides)
    return MatchResult(document_id=document_id, **defaults)


# Bucket fixtures (SYNTHETIC_DATA_SPEC.md "The invoice mix")
def clean_invoice(doc_id: str) -> MatchResult:
    return make_match(doc_id, amount_delta=0.40, date_delta_days=1)


def fabricated_invoice(doc_id: str) -> MatchResult:
    return make_match(doc_id, matched=False, ledger_txn_id=None)


def mismatch_invoice(doc_id: str) -> MatchResult:
    return make_match(doc_id, ledger_txn_id="txn-9", amount_delta=1350.50, date_delta_days=0)


# ---------------------------------------------------------------------------
# score_invoice — the three fraud signals
# ---------------------------------------------------------------------------
class TestScoreInvoice:
    def test_fabricated_invoice_is_high(self):
        flags = score_invoice(fabricated_invoice("doc-fab"))
        assert len(flags) == 1
        assert flags[0].signal == "missing_ledger_match"
        assert flags[0].severity == "high"

    def test_amount_mismatch_beyond_tolerance_is_medium(self):
        flags = score_invoice(make_match(amount_delta=AMOUNT_TOLERANCE_SAR + 0.01))
        assert [f.signal for f in flags] == ["amount_date_mismatch"]
        assert flags[0].severity == "medium"

    def test_date_mismatch_beyond_window_is_medium(self):
        flags = score_invoice(make_match(date_delta_days=DATE_WINDOW_DAYS + 1))
        assert [f.signal for f in flags] == ["amount_date_mismatch"]
        assert flags[0].severity == "medium"

    def test_negative_deltas_use_absolute_value(self):
        assert score_invoice(make_match(amount_delta=-(AMOUNT_TOLERANCE_SAR + 5)))
        assert score_invoice(make_match(date_delta_days=-(DATE_WINDOW_DAYS + 2)))

    def test_within_tolerance_is_clean(self):
        flags = score_invoice(
            make_match(amount_delta=AMOUNT_TOLERANCE_SAR, date_delta_days=DATE_WINDOW_DAYS)
        )
        assert flags == []

    def test_round_amount_is_medium(self):
        flags = score_invoice(make_match(is_round_amount=True))
        assert [f.signal for f in flags] == ["round_or_repeated_amount"]
        assert flags[0].severity == "medium"

    def test_repeated_amount_is_medium(self):
        flags = score_invoice(make_match(is_repeated_amount=True))
        assert [f.signal for f in flags] == ["round_or_repeated_amount"]
        assert flags[0].severity == "medium"

    def test_fabricated_and_round_stack(self):
        flags = score_invoice(make_match(matched=False, ledger_txn_id=None, is_round_amount=True))
        assert {f.signal for f in flags} == {"missing_ledger_match", "round_or_repeated_amount"}
        assert {f.severity for f in flags} == {"high", "medium"}


# ---------------------------------------------------------------------------
# build_forensic_report — roll-up
# ---------------------------------------------------------------------------
class TestBuildForensicReport:
    def test_fabricated_invoice_goes_red(self):
        report = build_forensic_report(
            [clean_invoice("doc-1"), fabricated_invoice("doc-2")]
        )
        assert report.overall_status == "red"
        assert any(f.severity == "high" for f in report.discrepancy_flags)
        assert report.reconciliation_rate == pytest.approx(0.5)

    def test_genuine_mismatch_goes_yellow_when_no_highs(self):
        report = build_forensic_report(
            [clean_invoice("doc-1"), mismatch_invoice("doc-2")]
        )
        assert report.overall_status == "yellow"
        assert all(f.severity == "medium" for f in report.discrepancy_flags)
        assert report.reconciliation_rate == pytest.approx(0.5)

    def test_all_clean_goes_green_with_full_reconciliation(self):
        report = build_forensic_report([clean_invoice(f"doc-{i}") for i in range(5)])
        assert report.overall_status == "green"
        assert report.discrepancy_flags == []
        assert report.reconciliation_rate == 1.0

    def test_empty_batch_is_green(self):
        report = build_forensic_report([])
        assert report.overall_status == "green"
        assert report.reconciliation_rate == 1.0

    def test_mixed_set_reflects_the_mix(self):
        # 17 clean + 1 fabricated + 2 mismatched = 20 -> matches the
        # schema_mapping.md Node 2 example: rate 0.85, status driven by the
        # high flag.
        matches = (
            [clean_invoice(f"doc-{i}") for i in range(17)]
            + [fabricated_invoice("doc-fab")]
            + [mismatch_invoice("doc-m1"), mismatch_invoice("doc-m2")]
        )
        report = build_forensic_report(matches)
        assert report.reconciliation_rate == pytest.approx(0.85)
        assert report.overall_status == "red"
        assert len(report.discrepancy_flags) == 3

    def test_report_round_trips_through_json(self):
        # Persist contract: agent_results stores model_dump(mode="json").
        report = build_forensic_report(
            [clean_invoice("doc-1"), fabricated_invoice("doc-2"), mismatch_invoice("doc-3")]
        )
        restored = ForensicReport.model_validate(report.model_dump(mode="json"))
        assert restored == report

    def test_describe_callable_cannot_change_severity(self):
        from models import DiscrepancyFlag

        def hostile_describe(raw_flags):
            return [DiscrepancyFlag(severity="low", description=f"text {i}") for i in range(len(raw_flags))]

        report = build_forensic_report([fabricated_invoice("doc-1")], describe=hostile_describe)
        assert report.discrepancy_flags[0].severity == "high"
        assert report.discrepancy_flags[0].description == "text 0"
        assert report.overall_status == "red"


# ---------------------------------------------------------------------------
# Matching-step helpers
# ---------------------------------------------------------------------------
class TestSignalHelpers:
    def test_round_amounts(self):
        assert is_suspiciously_round(5000.00)
        assert is_suspiciously_round(1500.00)
        assert not is_suspiciously_round(1500.50)
        assert not is_suspiciously_round(100.00)  # below threshold

    def test_repeated_amounts(self):
        amounts = {f"doc-{i}": 2500.00 for i in range(REPEATED_AMOUNT_MIN_COUNT)}
        amounts["doc-unique"] = 731.25
        repeated = repeated_amount_document_ids(amounts)
        assert repeated == {f"doc-{i}" for i in range(REPEATED_AMOUNT_MIN_COUNT)}


# ---------------------------------------------------------------------------
# explain.py deterministic fallback (no LLM: the wrapper is forced to fail)
# ---------------------------------------------------------------------------
class TestFallbackDescriptions:
    @pytest.fixture(autouse=True)
    def no_llm(self, monkeypatch):
        def boom(*args, **kwargs):
            raise explain.LLMError("forced failure for test")

        monkeypatch.setattr(explain, "complete", boom)

    def test_mismatch_fallback_cites_concrete_numbers(self):
        raw = score_invoice(mismatch_invoice("doc-m1"))
        ctx = {
            "doc-m1": InvoiceContext(
                vendor="Gulf Fuel Depot",
                invoice_amount=1500.50,
                invoice_date=date(2025, 10, 12),
                ledger_amount=150.00,
                ledger_date=date(2025, 10, 12),
            )
        }
        flags = write_flag_descriptions(raw, ctx)
        assert len(flags) == 1
        assert flags[0].severity == "medium"
        assert "1500.50" in flags[0].description
        assert "150.00" in flags[0].description
        assert "2025-10-12" in flags[0].description

    def test_fabricated_fallback_cites_amount_and_date(self):
        raw = score_invoice(fabricated_invoice("doc-fab"))
        ctx = {
            "doc-fab": InvoiceContext(
                vendor="Desert Traders", invoice_amount=9000.00, invoice_date=date(2025, 11, 3)
            )
        }
        flags = write_flag_descriptions(raw, ctx)
        assert flags[0].severity == "high"
        assert "9000.00" in flags[0].description
        assert "no matching transaction" in flags[0].description

    def test_missing_context_still_produces_text(self):
        raw = score_invoice(fabricated_invoice("doc-x"))
        flags = write_flag_descriptions(raw, {})
        assert flags[0].description
        assert "doc-x" in flags[0].description
