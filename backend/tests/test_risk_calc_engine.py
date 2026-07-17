"""
DB-free / LLM-free tests for core/risk_calc_engine.py — the Risk Sandbox math layer
(architecture.md §3; CONVENTIONS.md golden rule #2). Mirrors the other node test
files: pure pytest, no Supabase, no model calls, nothing time-dependent.

Covers determinism, a stable non-negative baseline, per-slider directionality,
extreme-value finiteness, classify_risk boundaries, and the <50ms perf target.
"""
from __future__ import annotations

import math
import time

import pytest

from core.risk_calc_engine import (
    MONTH_LABELS,
    SLIDERS,
    classify_risk,
    compute_risk_score,
    project_12_months,
    recalculate,
)
from models import RiskBaseline, RiskProjection, ScenarioDeltas


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def make_baseline(**overrides) -> RiskBaseline:
    """A healthy, seeded-SME-shaped baseline (schema_mapping.md §2 Node 5 example)."""
    data = dict(
        base_default_probability=0.12,
        revenue_volatility_multiplier=1.05,
        cash_buffer_months=3.2,
        recommended_interest_rate=0.08,
    )
    data.update(overrides)
    return RiskBaseline(**data)


def make_deltas(**overrides) -> ScenarioDeltas:
    return ScenarioDeltas(**overrides)


ZERO = make_deltas()  # all deltas 0 == baseline scenario


# ---------------------------------------------------------------------------
# Slider definitions
# ---------------------------------------------------------------------------
class TestSliders:
    def test_exactly_the_six_scenario_delta_fields(self):
        slider_keys = {s.key for s in SLIDERS}
        delta_fields = set(ScenarioDeltas.model_fields.keys())
        assert slider_keys == delta_fields
        assert len(SLIDERS) == 6

    def test_defaults_are_zero(self):
        for s in SLIDERS:
            assert s.default == 0.0, f"{s.key} default should be 0 (no change from baseline)"

    def test_default_within_range(self):
        for s in SLIDERS:
            assert s.min <= s.default <= s.max, f"{s.key} default outside [min, max]"

    def test_churn_is_one_directional(self):
        churn = next(s for s in SLIDERS if s.key == "customer_churn")
        assert churn.min == 0.0, "churn should not go negative (you can't un-churn)"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
class TestDeterminism:
    def test_same_input_same_output_three_runs(self):
        baseline = make_baseline()
        deltas = make_deltas(revenue_growth=0.1, cost_increase=0.05, interest_rate=0.02)
        results = [recalculate(baseline, deltas).model_dump() for _ in range(3)]
        assert results[0] == results[1] == results[2]

    def test_projection_is_deterministic(self):
        baseline = make_baseline()
        deltas = make_deltas(demand_shift=0.3)
        a = project_12_months(baseline, deltas)
        b = project_12_months(baseline, deltas)
        assert a == b


# ---------------------------------------------------------------------------
# Baseline behaviour
# ---------------------------------------------------------------------------
class TestBaseline:
    def test_baseline_non_negative_and_stable(self):
        _, cash_flow = project_12_months(make_baseline(), ZERO)
        assert len(cash_flow) == 12
        assert all(v >= 0 for v in cash_flow), "baseline cash flow must be non-negative"
        # No seasonality/growth deltas -> a flat line (all months identical).
        assert len(set(cash_flow)) == 1, "baseline curve should be stable/flat"

    def test_baseline_returns_valid_projection(self):
        proj = recalculate(make_baseline(), ZERO)
        assert isinstance(proj, RiskProjection)
        assert proj.months == MONTH_LABELS
        assert len(proj.cash_flow) == 12
        assert proj.risk_class == "low"  # healthy baseline
        # Round-trips through JSON like every other model output.
        restored = RiskProjection.model_validate(proj.model_dump(mode="json"))
        assert restored == proj

    def test_all_values_finite(self):
        _, cash_flow = project_12_months(make_baseline(), ZERO)
        assert all(math.isfinite(v) for v in cash_flow)


# ---------------------------------------------------------------------------
# Per-slider directionality
# ---------------------------------------------------------------------------
class TestSliderDirection:
    def _last(self, deltas) -> float:
        return project_12_months(make_baseline(), deltas)[1][-1]

    def _mean(self, deltas) -> float:
        cf = project_12_months(make_baseline(), deltas)[1]
        return sum(cf) / len(cf)

    def test_revenue_growth_raises_final_month(self):
        assert self._last(make_deltas(revenue_growth=0.2)) > self._last(ZERO)

    def test_cost_increase_lowers_cash_flow(self):
        assert self._mean(make_deltas(cost_increase=0.3)) < self._mean(ZERO)

    def test_customer_churn_lowers_final_month(self):
        assert self._last(make_deltas(customer_churn=0.3)) < self._last(ZERO)

    def test_interest_rate_lowers_cash_flow(self):
        assert self._mean(make_deltas(interest_rate=0.05)) < self._mean(ZERO)

    def test_oil_price_sensitivity_lowers_cash_flow(self):
        assert self._mean(make_deltas(oil_price_sensitivity=0.4)) < self._mean(ZERO)

    def test_demand_shift_changes_shape_not_broken(self):
        # Seasonal amplitude: it reshapes the curve (adds volatility) rather than
        # moving the mean, so assert the curve actually changes and stays finite.
        base_cf = project_12_months(make_baseline(), ZERO)[1]
        shifted_cf = project_12_months(make_baseline(), make_deltas(demand_shift=0.4))[1]
        assert shifted_cf != base_cf
        assert all(math.isfinite(v) for v in shifted_cf)
        # A positive demand_shift lifts early months (sin > 0 for months M2..M6).
        assert shifted_cf[2] > base_cf[2]


# ---------------------------------------------------------------------------
# Extreme values — no throw, stay finite
# ---------------------------------------------------------------------------
class TestExtremes:
    def test_slider_range_extremes_are_finite(self):
        for s in SLIDERS:
            for value in (s.min, s.max):
                deltas = make_deltas(**{s.key: value})
                proj = recalculate(make_baseline(), deltas)
                assert all(math.isfinite(v) for v in proj.cash_flow)
                assert 0.0 <= proj.risk_score <= 1.0
                assert proj.risk_class in ("low", "medium", "high")

    def test_all_sliders_at_worst_case_together(self):
        worst = make_deltas(
            revenue_growth=-0.30,
            cost_increase=0.40,
            customer_churn=0.50,
            demand_shift=0.40,
            interest_rate=0.08,
            oil_price_sensitivity=0.50,
        )
        proj = recalculate(make_baseline(), worst)
        assert all(math.isfinite(v) for v in proj.cash_flow)
        assert 0.0 <= proj.risk_score <= 1.0
        assert proj.risk_class == "high"

    def test_degenerate_baseline_does_not_throw(self):
        # Zero buffer / zero volatility guards must hold (no div-by-zero, no NaN).
        edge = make_baseline(cash_buffer_months=0.0, revenue_volatility_multiplier=0.0)
        proj = recalculate(edge, ZERO)
        assert all(math.isfinite(v) for v in proj.cash_flow)


# ---------------------------------------------------------------------------
# classify_risk boundaries
# ---------------------------------------------------------------------------
class TestClassifyRisk:
    def test_below_low_threshold(self):
        assert classify_risk(0.149) == "low"

    def test_at_low_threshold_is_medium(self):
        assert classify_risk(0.15) == "medium"

    def test_below_high_threshold(self):
        assert classify_risk(0.349) == "medium"

    def test_at_high_threshold_is_high(self):
        assert classify_risk(0.35) == "high"

    def test_extremes(self):
        assert classify_risk(0.0) == "low"
        assert classify_risk(1.0) == "high"


# ---------------------------------------------------------------------------
# Risk score bounds
# ---------------------------------------------------------------------------
class TestRiskScore:
    def test_score_in_unit_interval(self):
        for deltas in (ZERO, make_deltas(cost_increase=0.4, customer_churn=0.5)):
            _, cf = project_12_months(make_baseline(), deltas)
            score = compute_risk_score(make_baseline(), deltas, cf)
            assert 0.0 <= score <= 1.0

    def test_worse_scenario_scores_higher(self):
        base_bl = make_baseline()
        _, cf_good = project_12_months(base_bl, ZERO)
        bad = make_deltas(cost_increase=0.4, customer_churn=0.5, interest_rate=0.08)
        _, cf_bad = project_12_months(base_bl, bad)
        assert compute_risk_score(base_bl, bad, cf_bad) > compute_risk_score(base_bl, ZERO, cf_good)


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
class TestPerformance:
    def test_recalculate_under_50ms_mean_over_100_runs(self):
        baseline = make_baseline()
        deltas = make_deltas(revenue_growth=0.1, cost_increase=0.05, demand_shift=0.2)
        durations_ms: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            recalculate(baseline, deltas)
            durations_ms.append((time.perf_counter() - t0) * 1000.0)
        mean_ms = sum(durations_ms) / len(durations_ms)
        max_ms = max(durations_ms)
        assert mean_ms < 50.0, f"mean {mean_ms:.3f}ms exceeds 50ms target"
        # generous headroom on the single worst run too
        assert max_ms < 50.0, f"max {max_ms:.3f}ms exceeds 50ms target"
