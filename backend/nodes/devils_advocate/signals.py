"""
Devil's Advocate — pure-Python weakness signal computation (architecture.md
§1, schema_mapping.md Node 3, CONVENTIONS.md rule 1: matching/scoring is
Python, the LLM only writes text).

Reads mock_open_banking_ledger rows (both debit and credit — see
nodes/devils_advocate/ledger.py::fetch_ledger_rows) and extracted_documents,
and grades four business-model weaknesses. No model is called here —
narrate.py writes the LLM prose from these numbers.

Ledger schema note (confirmed against mock_open_banking_ledger, matches
nodes/forensic/matching.py): id, cr_number, transaction_date, amount,
description, transaction_type ('credit'|'debit'). There is NO counterparty
column. data/generate_synthetic_data.py bakes the counterparty into
`description` as "{description} — {counterparty}" before insert, so
_counterparty() below parses it back out of that suffix — a pattern every
debit row (supplier payments, recurring rent/payroll/fuel/...) follows.
Credit (revenue) rows are the exception: every single one of them uses the
same fixed counterparty label ("Customer receipts") — there is no per-client
breakdown anywhere in the synthetic ledger. compute_client_concentration
still does the real grouping (so it activates automatically if a genuine
per-client column ever ships); against this dataset it correctly reports
"not assessable" rather than inventing a fake split.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import mean, pstdev
from typing import Any, Mapping

from models import DocumentJSON, Severity

# ---------------------------------------------------------------------------
# Rubric constants (Salman-tunable — defensible defaults, not measured).
# ---------------------------------------------------------------------------
VENDOR_CONCENTRATION_HIGH = 0.75
VENDOR_CONCENTRATION_MEDIUM = 0.60
VENDOR_CONCENTRATION_HIGH_PENALTY = 25
VENDOR_CONCENTRATION_MEDIUM_PENALTY = 12

CLIENT_CONCENTRATION_HIGH = 0.50
CLIENT_CONCENTRATION_MEDIUM = 0.35
CLIENT_CONCENTRATION_HIGH_PENALTY = 25
CLIENT_CONCENTRATION_MEDIUM_PENALTY = 12

REVENUE_CV_HIGH = 0.50
REVENUE_CV_MEDIUM = 0.30
REVENUE_CV_HIGH_PENALTY = 20
REVENUE_CV_MEDIUM_PENALTY = 10

SECTOR_COST_EXPOSURE_MEDIUM = 0.40
SECTOR_COST_EXPOSURE_MEDIUM_PENALTY = 10

# A concentration/volatility ratio needs at least this many independent rows
# (per side, per month) before it's treated as a real signal rather than an
# artifact of a tiny sample (e.g. one debit row is trivially "100%").
MIN_ROWS_FOR_ASSESSMENT = 2

# --- Sector cost-category keyword map (STEP 0 finding) ---------------------
# Built from the REAL seeded vendor list (data/generate_synthetic_data.py
# ::VENDORS), not invented names. That script assigns a vendor to every
# invoice with rng.choice(VENDORS) — uniformly at random, regardless of
# sector — so this signal will rarely fire against the current demo seed by
# construction. It is still the correct, non-fabricated mapping: it activates
# for real data (or once vendor assignment becomes sector-aware) without any
# code change.
_VENDOR_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fuel": ("fuel", "diesel"),
    "industrial_materials": ("sabic", "polymers", "contracting"),
    "trading_supplies": ("trading", "supplies", "almarai", "jarir"),
}
SECTOR_CRITICAL_CATEGORY: dict[str, str] = {
    "logistics": "fuel",
    "cafe": "trading_supplies",
    "construction_supplier": "industrial_materials",
    "retail": "trading_supplies",
    "manufacturer": "industrial_materials",
}


@dataclass(frozen=True)
class SignalResult:
    """One graded weakness signal. `triggered`/`severity`/`penalty` are
    decided HERE and are final — narrate.py may only add prose, never
    regrade (mirrors nodes/forensic/scoring.py::RawFlag). `detail` carries
    the concrete numbers the narrator cites."""

    signal: str
    assessable: bool
    metric: float | None
    triggered: bool
    severity: Severity | None
    penalty: int
    detail: Mapping[str, Any] = field(default_factory=dict)


def _counterparty(description: str | None) -> str:
    """Parses the payee/counterparty out of a ledger description built by
    generate_synthetic_data.py as "{description} — {counterparty}". Rows
    that don't follow the pattern (or have no description) fall back to the
    whole string / "unknown" rather than crashing."""
    if not description:
        return "unknown"
    if " — " in description:
        tail = description.rsplit(" — ", 1)[1].strip()
        return tail or "unknown"
    return description.strip() or "unknown"


def _month_key(value: Any) -> tuple[int, int]:
    if isinstance(value, date):
        d = value
    else:
        d = datetime.fromisoformat(str(value)).date()
    return (d.year, d.month)


def compute_vendor_concentration(debit_rows: list[dict[str, Any]]) -> SignalResult:
    """Share of total outflow (debit) SAR going to the single largest
    payee, parsed from the ledger description (there is no dedicated
    vendor/counterparty column — see module docstring). Covers both
    recurring cost categories (rent/payroll/fuel/...) and one-off supplier
    payments; either kind concentrating spend is a genuine fragility
    signal."""
    if len(debit_rows) < MIN_ROWS_FOR_ASSESSMENT:
        return SignalResult("vendor_concentration", False, None, False, None, 0)

    totals: dict[str, float] = defaultdict(float)
    for row in debit_rows:
        totals[_counterparty(row.get("description"))] += abs(float(row["amount"]))

    total_spend = sum(totals.values())
    if total_spend <= 0:
        return SignalResult("vendor_concentration", False, None, False, None, 0)

    top_counterparty, top_amount = max(totals.items(), key=lambda kv: kv[1])
    share = top_amount / total_spend

    if share > VENDOR_CONCENTRATION_HIGH:
        severity, penalty, triggered = "high", VENDOR_CONCENTRATION_HIGH_PENALTY, True
    elif share > VENDOR_CONCENTRATION_MEDIUM:
        severity, penalty, triggered = "medium", VENDOR_CONCENTRATION_MEDIUM_PENALTY, True
    else:
        severity, penalty, triggered = None, 0, False

    return SignalResult(
        "vendor_concentration", True, share, triggered, severity, penalty,
        detail={
            "top_counterparty": top_counterparty, "share": share,
            "top_amount_sar": top_amount, "total_debit_sar": total_spend,
        },
    )


def compute_client_concentration(credit_rows: list[dict[str, Any]]) -> SignalResult:
    """Share of total inflow (credit) SAR from the single largest
    counterparty. Only assessable if the ledger actually distinguishes
    clients — mock_open_banking_ledger does not (every credit row shares
    the "Customer receipts" label), so this genuinely returns
    assessable=False against the current synthetic dataset (module
    docstring), not a hardcoded shortcut."""
    if len(credit_rows) < MIN_ROWS_FOR_ASSESSMENT:
        return SignalResult("client_concentration", False, None, False, None, 0)

    totals: dict[str, float] = defaultdict(float)
    for row in credit_rows:
        totals[_counterparty(row.get("description"))] += abs(float(row["amount"]))

    if len(totals) < 2:
        return SignalResult(
            "client_concentration", False, None, False, None, 0,
            detail={"reason": "ledger has no per-client breakdown"},
        )

    total_revenue = sum(totals.values())
    if total_revenue <= 0:
        return SignalResult("client_concentration", False, None, False, None, 0)

    top_client, top_amount = max(totals.items(), key=lambda kv: kv[1])
    share = top_amount / total_revenue

    if share > CLIENT_CONCENTRATION_HIGH:
        severity, penalty, triggered = "high", CLIENT_CONCENTRATION_HIGH_PENALTY, True
    elif share > CLIENT_CONCENTRATION_MEDIUM:
        severity, penalty, triggered = "medium", CLIENT_CONCENTRATION_MEDIUM_PENALTY, True
    else:
        severity, penalty, triggered = None, 0, False

    return SignalResult(
        "client_concentration", True, share, triggered, severity, penalty,
        detail={
            "top_client": top_client, "share": share,
            "top_amount_sar": top_amount, "total_revenue_sar": total_revenue,
        },
    )


def compute_revenue_volatility(credit_rows: list[dict[str, Any]]) -> SignalResult:
    """Coefficient of variation (population stdev / mean) of monthly
    revenue. Credit rows are summed into calendar-month buckets first so
    multiple credit rows landing in one month don't inflate variance."""
    if len(credit_rows) < MIN_ROWS_FOR_ASSESSMENT:
        return SignalResult("revenue_volatility", False, None, False, None, 0)

    monthly: dict[tuple[int, int], float] = defaultdict(float)
    for row in credit_rows:
        monthly[_month_key(row["transaction_date"])] += float(row["amount"])

    values = list(monthly.values())
    if len(values) < MIN_ROWS_FOR_ASSESSMENT:
        return SignalResult("revenue_volatility", False, None, False, None, 0)

    avg = mean(values)
    if avg <= 0:
        return SignalResult("revenue_volatility", False, None, False, None, 0)

    cv = pstdev(values) / avg

    if cv > REVENUE_CV_HIGH:
        severity, penalty, triggered = "high", REVENUE_CV_HIGH_PENALTY, True
    elif cv > REVENUE_CV_MEDIUM:
        severity, penalty, triggered = "medium", REVENUE_CV_MEDIUM_PENALTY, True
    else:
        severity, penalty, triggered = None, 0, False

    return SignalResult(
        "revenue_volatility", True, cv, triggered, severity, penalty,
        detail={
            "coefficient_of_variation": cv, "monthly_mean_sar": avg,
            "monthly_stdev_sar": pstdev(values), "months_observed": len(values),
        },
    )


def compute_sector_cost_exposure(
    documents: list[DocumentJSON], sector: str | None
) -> SignalResult:
    """Share of total invoice value paid to vendors matching the sector's
    single most fragility-relevant cost category (SECTOR_CRITICAL_CATEGORY /
    _VENDOR_CATEGORY_KEYWORDS above, built from the real seeded vendor
    list — STEP 0). Unknown/missing sector or no documents -> not
    assessable, never a crash."""
    category = SECTOR_CRITICAL_CATEGORY.get(sector or "")
    if category is None or not documents:
        return SignalResult("sector_cost_exposure", False, None, False, None, 0)

    keywords = _VENDOR_CATEGORY_KEYWORDS[category]
    total = 0.0
    matched = 0.0
    for doc in documents:
        total += doc.extracted_amount
        vendor = (doc.vendor or "").lower()
        if any(keyword in vendor for keyword in keywords):
            matched += doc.extracted_amount

    if total <= 0:
        return SignalResult("sector_cost_exposure", False, None, False, None, 0)

    share = matched / total
    if share > SECTOR_COST_EXPOSURE_MEDIUM:
        severity, penalty, triggered = "medium", SECTOR_COST_EXPOSURE_MEDIUM_PENALTY, True
    else:
        severity, penalty, triggered = None, 0, False

    return SignalResult(
        "sector_cost_exposure", True, share, triggered, severity, penalty,
        detail={
            "sector": sector, "category": category, "share": share,
            "matched_amount_sar": matched, "total_invoice_sar": total,
        },
    )


def compute_all_signals(
    *,
    debit_rows: list[dict[str, Any]],
    credit_rows: list[dict[str, Any]],
    documents: list[DocumentJSON],
    sector: str | None,
) -> list[SignalResult]:
    """Runs all four signals in the fixed rubric order."""
    return [
        compute_vendor_concentration(debit_rows),
        compute_client_concentration(credit_rows),
        compute_revenue_volatility(credit_rows),
        compute_sector_cost_exposure(documents, sector),
    ]


__all__ = [
    "VENDOR_CONCENTRATION_HIGH",
    "VENDOR_CONCENTRATION_MEDIUM",
    "VENDOR_CONCENTRATION_HIGH_PENALTY",
    "VENDOR_CONCENTRATION_MEDIUM_PENALTY",
    "CLIENT_CONCENTRATION_HIGH",
    "CLIENT_CONCENTRATION_MEDIUM",
    "CLIENT_CONCENTRATION_HIGH_PENALTY",
    "CLIENT_CONCENTRATION_MEDIUM_PENALTY",
    "REVENUE_CV_HIGH",
    "REVENUE_CV_MEDIUM",
    "REVENUE_CV_HIGH_PENALTY",
    "REVENUE_CV_MEDIUM_PENALTY",
    "SECTOR_COST_EXPOSURE_MEDIUM",
    "SECTOR_COST_EXPOSURE_MEDIUM_PENALTY",
    "MIN_ROWS_FOR_ASSESSMENT",
    "SECTOR_CRITICAL_CATEGORY",
    "SignalResult",
    "compute_vendor_concentration",
    "compute_client_concentration",
    "compute_revenue_volatility",
    "compute_sector_cost_exposure",
    "compute_all_signals",
]
