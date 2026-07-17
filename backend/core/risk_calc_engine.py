"""
risk_calc_engine.py — the CORE MATH LAYER for the Risk Sandbox
(architecture.md §3; CONVENTIONS.md golden rule #2).

This module is deliberately NON-LLM and lives OUTSIDE the LangGraph. It is plain,
deterministic Python: a 12-month cash-flow projection with per-slider multiplier
adjustments, a risk score, a risk class, and a one-line English summary. The FastAPI
endpoint (next prompt) loads the precomputed `RiskBaseline` server-side and calls
`recalculate(baseline, deltas)` on every slider move — no model round-trip ever.

Contract (models.py — the single source of truth, NOT redefined here):
    recalculate(baseline: RiskBaseline, deltas: ScenarioDeltas) -> RiskProjection

Determinism guarantee: the same (baseline, deltas) input ALWAYS produces byte-identical
output. No randomness, no wall-clock, no I/O. This is what makes the demo repeatable.

Units: every slider delta is a FRACTION, not a percentage (e.g. revenue_growth = 0.20
means +20%). The UI multiplies by 100 for display; see SLIDERS[*].unit.

Requires: pydantic>=2 (already a project dep). Stdlib `math`/`statistics` only — no
numpy/pandas. A single recalculate() call is well under 50 ms (see the perf test).
"""
from __future__ import annotations

import math
import statistics
from typing import Literal

from pydantic import BaseModel, Field

from models import RiskBaseline, RiskClass, RiskProjection, ScenarioDeltas

# ---------------------------------------------------------------------------
# Grounding constants
# ---------------------------------------------------------------------------
# REVENUE_ANCHOR is the median monthly revenue across the 6 seeded SMEs in
# data/generate_synthetic_data.py (sector midpoints: cafe 90k, retail 122.5k x2,
# manufacturer 200k, logistics 220k, construction 280k -> median ~161k). Anchoring
# here keeps every projection in the same order of magnitude as the demo ledger.
REVENUE_ANCHOR: float = 160_000.0
# The buffer a "typical" seeded SME carries; implied revenue scales relative to it.
REFERENCE_BUFFER_MONTHS: float = 3.0
# Baseline share of revenue consumed by cost -> a 20% net operating margin before
# any slider moves. Grounded in the seeded sector cost stacks (rent+payroll+inputs
# land in the ~75-85% band).
BASE_COST_RATIO: float = 0.80
# Sector coupling for oil_price_sensitivity. Sector-specific coefficients are OUT OF
# SCOPE for this prompt (Salman's realism pass) — this is the plumbing, default 1.0.
DEFAULT_OIL_SECTOR_COEFF: float = 1.0

_EPS: float = 1e-9


# ---------------------------------------------------------------------------
# Slider definitions — importable so the endpoint and the React UI render them
# ---------------------------------------------------------------------------
class SliderSpec(BaseModel):
    """One sandbox slider. `key` matches a field on models.ScenarioDeltas exactly.

    `min`/`max`/`default` are in the SAME fractional units as the delta value the
    client sends back (default = 0.0 = no change from baseline). `unit` tells the UI
    how to render the value ("%" -> value*100 with a percent sign; "index" -> raw
    coefficient). `modifies` is a human-readable note on which baseline quantity the
    slider drives and how — surfaced as slider help text.
    """

    key: str
    label: str
    min: float
    max: float
    default: float = 0.0
    unit: Literal["%", "index"]
    modifies: str


# The 6 sliders are EXACTLY the 6 fields on ScenarioDeltas — no more, no less.
# Ranges follow the suggested list; deviations are documented inline.
SLIDERS: list[SliderSpec] = [
    SliderSpec(
        key="revenue_growth",
        label="Revenue growth",
        min=-0.30,
        max=0.30,
        default=0.0,
        unit="%",
        modifies="Monthly compounding growth rate applied to implied revenue.",
    ),
    SliderSpec(
        key="cost_increase",
        label="Cost increase",
        min=-0.20,
        max=0.40,
        default=0.0,
        unit="%",
        modifies="Multiplier on the monthly cost base (asymmetric: costs rise faster than they fall).",
    ),
    SliderSpec(
        key="customer_churn",
        label="Customer churn",
        min=0.0,
        max=0.50,
        default=0.0,
        unit="%",
        modifies="One-directional compounding revenue drag (you cannot 'un-churn' customers).",
    ),
    SliderSpec(
        key="demand_shift",
        label="Demand shift",
        min=-0.40,
        max=0.40,
        default=0.0,
        unit="%",
        modifies="Seasonal amplitude modifier (sine wave over the 12 months).",
    ),
    SliderSpec(
        key="interest_rate",
        label="Interest rate",
        min=-0.03,
        max=0.08,
        default=0.0,
        unit="%",
        modifies="Delta (in rate points) on recommended_interest_rate; drives a debt-service drag scaled by cash_buffer_months.",
    ),
    SliderSpec(
        key="oil_price_sensitivity",
        label="Oil price sensitivity",
        min=-0.50,
        max=0.50,
        default=0.0,
        unit="index",
        modifies="Cost multiplier weighted by a sector oil coefficient (default 1.0; sector-specific coefficients deferred).",
    ),
]

# Static 12-month labels. Localisation (Arabic month names) is the UI's job.
MONTH_LABELS: list[str] = [f"M{i}" for i in range(1, 13)]


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------
def _implied_monthly_revenue(baseline: RiskBaseline) -> float:
    """Synthesize a starting monthly revenue from the baseline coefficients.

    RiskBaseline carries no explicit revenue, so we derive one: scale the demo-median
    anchor by how much runway the SME holds (cash_buffer_months vs the reference) and
    discount it by revenue volatility (a noisier top line implies a lower dependable
    monthly figure). Both factors are guarded to stay strictly positive.
    """
    buffer_factor = max(baseline.cash_buffer_months, 0.0) / REFERENCE_BUFFER_MONTHS
    vol = max(baseline.revenue_volatility_multiplier, _EPS)
    return REVENUE_ANCHOR * buffer_factor / vol


def project_12_months(
    baseline: RiskBaseline, deltas: ScenarioDeltas
) -> tuple[list[str], list[float]]:
    """Pure 12-month net-cash-flow projection. Returns (months, cash_flow).

    For month index i (0..11, i.e. M1..M12):

        rev_i  = implied_revenue
                 * (1 + revenue_growth) ** i           # compounding growth
                 * (1 - customer_churn) ** i           # compounding churn drag
                 * (1 + demand_shift * sin(2*pi*i/12))  # seasonal amplitude

        cost_frac = BASE_COST_RATIO
                    * (1 + cost_increase)                       # cost multiplier
                    * (1 + oil_price_sensitivity * OIL_COEFF)   # oil-weighted cost

        debt_i = implied_revenue * cash_buffer_months
                 * (recommended_interest_rate + interest_rate) / 12   # debt-service drag

        cash_flow_i = rev_i * (1 - cost_frac) - debt_i

    All terms are finite for any finite input, so no month can be inf/NaN.
    """
    implied = _implied_monthly_revenue(baseline)

    # Cost fraction is flat across the year (per-month multiplier, not compounding).
    cost_frac = (
        BASE_COST_RATIO
        * (1.0 + deltas.cost_increase)
        * (1.0 + deltas.oil_price_sensitivity * DEFAULT_OIL_SECTOR_COEFF)
    )

    # Debt-service drag: a notional balance-sheet size (revenue * buffer) serviced at
    # the effective annual rate, spread monthly. Raising interest_rate lifts the drag.
    effective_rate = baseline.recommended_interest_rate + deltas.interest_rate
    debt_service = implied * max(baseline.cash_buffer_months, 0.0) * effective_rate / 12.0

    growth = 1.0 + deltas.revenue_growth
    retention = 1.0 - deltas.customer_churn  # churn in [0, 0.5] -> retention in [0.5, 1]

    cash_flow: list[float] = []
    for i in range(12):
        seasonal = 1.0 + deltas.demand_shift * math.sin(2.0 * math.pi * i / 12.0)
        rev_i = implied * (growth**i) * (retention**i) * seasonal
        net_i = rev_i * (1.0 - cost_frac) - debt_service
        # Round for clean JSON / stable equality; math is deterministic regardless.
        cash_flow.append(round(net_i, 2))

    return list(MONTH_LABELS), cash_flow


def compute_risk_score(
    baseline: RiskBaseline, deltas: ScenarioDeltas, projection_cash_flow: list[float]
) -> float:
    """Blend the intrinsic default probability with the shape of the projected cash
    flow. Higher = riskier. Always in [0.0, 1.0].

    Components (weights sum to 1.0, so the raw blend is already in range):
      - base_default_probability (0.45): the SME's intrinsic risk.
      - trough_penalty          (0.30): how far the worst month dips below the mean.
      - coefficient of variation (0.10): month-to-month volatility.
      - negative-trough flag    (0.15): a hard penalty if any month goes cash-negative.
    """
    mean = statistics.fmean(projection_cash_flow)
    trough = min(projection_cash_flow)
    denom = abs(mean) + _EPS

    trough_penalty = min(1.0, max(0.0, (mean - trough) / denom))
    cv = min(1.0, statistics.pstdev(projection_cash_flow) / denom)
    neg_penalty = 1.0 if trough < 0.0 else 0.0

    score = (
        0.45 * baseline.base_default_probability
        + 0.30 * trough_penalty
        + 0.10 * cv
        + 0.15 * neg_penalty
    )
    return max(0.0, min(1.0, score))


def classify_risk(score: float) -> RiskClass:
    """Map a 0..1 risk score to the RiskClass literal from models.py.

    Thresholds: < 0.15 -> "low"  (near a healthy SME's intrinsic default probability
    with a stable, non-negative curve); < 0.35 -> "medium" (elevated volatility or a
    shallow trough, still serviceable); else -> "high" (a deep/negative trough or a
    high intrinsic default probability dominates).
    """
    if score < 0.15:
        return "low"
    if score < 0.35:
        return "medium"
    return "high"


def summary_line(
    baseline: RiskBaseline,
    deltas: ScenarioDeltas,
    projection_cash_flow: list[float],
    risk_class: RiskClass,
) -> str:
    """Compose a one-sentence English summary. Pure string work — NO LLM.
    Arabic is rendered UI-side from the structured RiskProjection, not here.
    """
    start = projection_cash_flow[0]
    end = projection_cash_flow[-1]
    end_delta_pct = (end - start) / (abs(start) + _EPS) * 100.0
    direction = "above" if end_delta_pct >= 0 else "below"

    trough_month = projection_cash_flow.index(min(projection_cash_flow)) + 1

    return (
        f"Under this scenario, cash flow ends {abs(end_delta_pct):.0f}% {direction} "
        f"its starting level, with the trough in month {trough_month}; "
        f"risk classified as {risk_class}."
    )


def recalculate(baseline: RiskBaseline, deltas: ScenarioDeltas) -> RiskProjection:
    """Top-level orchestration the FastAPI endpoint calls. Deterministic; no I/O.

    Runs the projection, scores it, classifies it, writes the summary, and returns a
    valid RiskProjection (models.py). Same input -> same output, every time.
    """
    months, cash_flow = project_12_months(baseline, deltas)
    score = compute_risk_score(baseline, deltas, cash_flow)
    risk_class = classify_risk(score)
    line = summary_line(baseline, deltas, cash_flow, risk_class)

    return RiskProjection(
        months=months,
        cash_flow=cash_flow,
        risk_score=round(score, 4),
        risk_class=risk_class,
        summary_line=line,
    )


__all__ = [
    "SliderSpec",
    "SLIDERS",
    "MONTH_LABELS",
    "project_12_months",
    "compute_risk_score",
    "classify_risk",
    "summary_line",
    "recalculate",
]
