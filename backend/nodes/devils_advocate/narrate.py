"""
Devil's Advocate — weakness/mitigation text (architecture.md §1). The ONLY
place in this node that calls a model, and it uses the FULL GPT-5.4 tier
(core/llm.py::complete_full) — the locked model table (architecture.md §1)
marks Devil's Advocate as a visible-quality node, unlike forensic/oracle's
Mini tier. The LLM writes the human-readable `critical_weaknesses` /
`mitigation_suggestions` sentences and NOTHING else — severity and
business_model_score are decided in signals.py / scoring.py and never sent
back through the model (mirrors nodes/forensic/explain.py).

Every LLM failure (missing key, API error, malformed reply) falls back to a
templated sentence built from the same concrete numbers, so this module can
never crash the graph.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.llm import LLMError, complete_full
from nodes.devils_advocate.signals import SignalResult

_SYSTEM_PROMPT = (
    "You are a skeptical credit risk analyst writing for a bank credit "
    "officer reviewing an SME loan application. For the business weakness "
    "described, reply with exactly two lines and nothing else:\n"
    "WEAKNESS: <one plain-English sentence stating the weakness, citing the "
    "exact figures you were given>\n"
    "MITIGATION: <one plain-English sentence suggesting what evidence the "
    "bank should request to mitigate it>\n"
    "State only the weakness — do not speculate about intent. Amounts are "
    "in SAR."
)


@dataclass(frozen=True)
class AdvocateContext:
    """Company framing for the narrator — all fields optional so the prompt
    degrades gracefully with partial sme_profile data."""

    company_name: str | None = None
    sector: str | None = None


@dataclass(frozen=True)
class WeaknessNarrative:
    critical_weaknesses: list[str]
    mitigation_suggestions: list[str]


def _facts(signal: SignalResult, ctx: AdvocateContext) -> list[str]:
    facts: list[str] = []
    if ctx.company_name:
        facts.append(f"Company: {ctx.company_name}")
    if ctx.sector:
        facts.append(f"Sector: {ctx.sector}")
    facts.append(f"Signal: {signal.signal}")
    for key, value in signal.detail.items():
        facts.append(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")
    return facts


def _fallback(signal: SignalResult) -> tuple[str, str]:
    """Deterministic templates from the same numbers, used whenever the LLM
    call fails or replies in an unparseable shape — mirrors
    nodes/forensic/explain.py::_fallback_description."""
    d = signal.detail
    if signal.signal == "vendor_concentration":
        weakness = (
            f"{d.get('top_counterparty', 'A single payee')} accounts for "
            f"{d.get('share', 0):.0%} of total outflow "
            f"({d.get('top_amount_sar', 0):.2f} of {d.get('total_debit_sar', 0):.2f} SAR) "
            f"— heavy reliance on one cost source."
        )
        mitigation = "Request evidence of a secondary supplier or contingency arrangement."
    elif signal.signal == "client_concentration":
        weakness = (
            f"{d.get('top_client', 'A single client')} accounts for "
            f"{d.get('share', 0):.0%} of total revenue "
            f"({d.get('top_amount_sar', 0):.2f} of {d.get('total_revenue_sar', 0):.2f} SAR) "
            f"— heavy reliance on one customer."
        )
        mitigation = "Request evidence of a diversified or growing client base."
    elif signal.signal == "revenue_volatility":
        weakness = (
            f"Monthly revenue swings with a coefficient of variation of "
            f"{d.get('coefficient_of_variation', 0):.2f} over {d.get('months_observed', 0)} "
            f"months (mean {d.get('monthly_mean_sar', 0):.2f} SAR, stdev "
            f"{d.get('monthly_stdev_sar', 0):.2f} SAR) — unpredictable cash flow."
        )
        mitigation = "Request a 12-month cash flow forecast and evidence of a cash buffer."
    elif signal.signal == "sector_cost_exposure":
        weakness = (
            f"{d.get('share', 0):.0%} of invoice value "
            f"({d.get('matched_amount_sar', 0):.2f} of {d.get('total_invoice_sar', 0):.2f} SAR) "
            f"is concentrated in the {d.get('category', 'a single')} cost category for a "
            f"{d.get('sector', 'this')} business — exposed to that input's price swings."
        )
        mitigation = (
            "Request evidence of hedging, fixed-price contracts, or an alternate supply "
            "source for that cost input."
        )
    else:
        weakness = f"Elevated {signal.signal} risk detected."
        mitigation = "Request supporting documentation to clarify this risk."
    return weakness, mitigation


def _parse_reply(reply: str) -> tuple[str, str]:
    weakness = None
    mitigation = None
    for line in reply.splitlines():
        line = line.strip()
        if line.upper().startswith("WEAKNESS:"):
            weakness = line.split(":", 1)[1].strip()
        elif line.upper().startswith("MITIGATION:"):
            mitigation = line.split(":", 1)[1].strip()
    if not weakness or not mitigation:
        raise ValueError("model reply did not contain both WEAKNESS and MITIGATION lines")
    return weakness, mitigation


def write_weakness_report(
    ranked_signals: list[SignalResult], context: AdvocateContext
) -> WeaknessNarrative:
    """One weakness + one mitigation sentence per ranked (already-triggered,
    already-ordered) signal, in the same order. Severity/score are never
    touched here — only prose."""
    weaknesses: list[str] = []
    mitigations: list[str] = []
    for signal in ranked_signals:
        try:
            reply = complete_full(
                "Write the WEAKNESS and MITIGATION lines for this finding:\n"
                + "\n".join(f"- {fact}" for fact in _facts(signal, context)),
                system=_SYSTEM_PROMPT,
            )
            weakness, mitigation = _parse_reply(reply)
        except (LLMError, ValueError):
            weakness, mitigation = _fallback(signal)
        weaknesses.append(weakness)
        mitigations.append(mitigation)
    return WeaknessNarrative(critical_weaknesses=weaknesses, mitigation_suggestions=mitigations)


__all__ = ["AdvocateContext", "WeaknessNarrative", "write_weakness_report"]
