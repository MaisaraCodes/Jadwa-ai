"""
Ground-truth oracle tests for the forensic scoring layer
(nodes/forensic/scoring.py), driven by data/ground_truth.json.

data/generate_synthetic_data.py writes ground_truth.json with one entry per
extracted document: which bucket it was planted in (legit / fabricated /
mismatch) and the expected_flag a correct forensic engine must produce. The
raw amounts/dates/ledger rows themselves live in Postgres, not in that JSON
(they're regenerated per-run with fresh document_id UUIDs) — so instead of
reconstructing exact figures, these tests reconstruct the MINIMAL MatchResult
that each bucket's own generator logic guarantees (see
generate_synthetic_data.py::build_ledger_and_docs) and assert score_invoice /
build_forensic_report reproduce the manifest's expected_flag. This is the
"real synthetic data" run promised in the forensic_accountant_node task —
re-run generate_synthetic_data.py and this file re-derives from whatever
ground_truth.json it emits next, no hardcoded document_ids required.

If ground_truth.json doesn't exist, these tests are skipped (not failed) —
see the fallback fixture tests in test_forensic_scoring.py for the
hand-built equivalent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nodes.forensic.scoring import (
    AMOUNT_TOLERANCE_SAR,
    DATE_WINDOW_DAYS,
    MatchResult,
    build_forensic_report,
    score_invoice,
)

GROUND_TRUTH_PATH = Path(__file__).resolve().parents[2] / "data" / "ground_truth.json"

if not GROUND_TRUTH_PATH.exists():
    pytest.skip(
        "data/ground_truth.json not found — run data/generate_synthetic_data.py "
        "to produce it, then re-run this file against the real synthetic data.",
        allow_module_level=True,
    )

_GROUND_TRUTH = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def _match_for_truth_entry(entry: dict) -> MatchResult:
    """Builds the MatchResult that build_ledger_and_docs' own construction
    of this bucket guarantees (see generate_synthetic_data.py):
      - legit: a debit within tolerance (0 delta) and within the date window.
      - fabricated: no candidate ledger row at all.
      - mismatch (amount signal): a debit ~10% off — always beyond
        AMOUNT_TOLERANCE_SAR.
      - mismatch (round/late signal): a round SAR 5,000 amount posted more
        than DATE_WINDOW_DAYS late.
    """
    bucket = entry["bucket"]
    reason = entry["reason"]

    if bucket == "legit":
        return MatchResult(document_id=entry["document_id"], matched=True)
    if bucket == "fabricated":
        return MatchResult(document_id=entry["document_id"], matched=False)

    assert bucket == "mismatch"
    if "amount differs" in reason:
        return MatchResult(
            document_id=entry["document_id"],
            matched=True,
            amount_delta=AMOUNT_TOLERANCE_SAR + 1.0,
        )
    assert "round" in reason
    return MatchResult(
        document_id=entry["document_id"],
        matched=True,
        date_delta_days=DATE_WINDOW_DAYS + 5,
        is_round_amount=True,
    )


class TestGroundTruthBuckets:
    """Every document_id in the manifest, scored via score_invoice, must
    reach the severity its own bucket implies."""

    @pytest.mark.parametrize(
        "sme",
        _GROUND_TRUTH["smes"],
        ids=[sme["company_name"] for sme in _GROUND_TRUTH["smes"]],
    )
    def test_bucket_severities_match_expected_flag(self, sme):
        for entry in sme["documents"]:
            match = _match_for_truth_entry(entry)
            flags = score_invoice(match)
            expected_flag = entry["expected_flag"]

            if expected_flag == "green":
                assert flags == [], entry
            elif expected_flag == "red":
                assert any(f.severity == "high" for f in flags), entry
            elif expected_flag == "yellow":
                assert flags and all(f.severity == "medium" for f in flags), entry
            else:
                pytest.fail(f"unknown expected_flag {expected_flag!r} in manifest")


class TestGroundTruthReportRollup:
    """build_forensic_report over one SME's full document set must land on
    the manifest's bucket mix — reconciliation_rate and overall_status."""

    @pytest.mark.parametrize(
        "sme",
        _GROUND_TRUTH["smes"],
        ids=[sme["company_name"] for sme in _GROUND_TRUTH["smes"]],
    )
    def test_report_rollup_matches_manifest_mix(self, sme):
        matches = [_match_for_truth_entry(entry) for entry in sme["documents"]]
        report = build_forensic_report(matches)

        legit_count = sum(1 for e in sme["documents"] if e["bucket"] == "legit")
        fabricated_count = sum(1 for e in sme["documents"] if e["bucket"] == "fabricated")

        assert report.reconciliation_rate == pytest.approx(legit_count / len(matches))
        # Every seeded persona carries exactly one fabricated (high-severity)
        # document (generate_synthetic_data.py PERSONAS), so overall_status
        # must be red whenever one is present.
        if fabricated_count:
            assert report.overall_status == "red"

    def test_rawad_matches_the_documented_demo_numbers(self):
        """DATA.md's headline claim: Rawad Logistics reconciles 17/20 (0.85),
        one fabricated SAR 1,500.50 receipt red, two mismatches yellow."""
        rawad = next(
            sme for sme in _GROUND_TRUTH["smes"] if sme["company_name"] == "Rawad Logistics"
        )
        matches = [_match_for_truth_entry(entry) for entry in rawad["documents"]]
        report = build_forensic_report(matches)

        expected_flag_count = sum(len(score_invoice(m)) for m in matches)

        assert len(matches) == 20
        assert report.reconciliation_rate == pytest.approx(0.85)
        assert report.overall_status == "red"
        assert len(report.discrepancy_flags) == expected_flag_count
        assert sum(1 for f in report.discrepancy_flags if f.severity == "high") == 1
        # The "round + late" mismatch document trips BOTH the date-window and
        # round-amount signals (two medium flags on one invoice) — this is
        # score_invoice's documented stacking behaviour, not a bug.
        assert sum(1 for f in report.discrepancy_flags if f.severity == "medium") == 3
