"""
Forensic accountant — flag description text (architecture.md §1).

This is the ONLY place in the forensic node where a model is called
(GPT-5.4 Mini via core/llm.py). The LLM writes the plain-language
`description` on each DiscrepancyFlag and NOTHING else — severity and
overall status are decided deterministically in scoring.py and are never
sent back through the model.

Every LLM failure falls back to a templated English description built from
the same concrete numbers, so this module can never crash the graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from core.llm import LLMError, complete
from models import DiscrepancyFlag
from nodes.forensic.scoring import RawFlag, default_flag_description

_SYSTEM_PROMPT = (
    "You write one-sentence, plain-English descriptions of accounting "
    "discrepancies for a bank credit officer reviewing an SME loan "
    "application. Use the exact figures and dates you are given (amounts in "
    "SAR, dates as YYYY-MM-DD). State only the discrepancy — do not judge "
    "severity, speculate about intent, or recommend actions. Reply with the "
    "sentence only."
)


@dataclass(frozen=True)
class InvoiceContext:
    """Concrete invoice/ledger figures for one document_id, so descriptions
    can cite real numbers instead of deltas. All fields optional — the
    templates degrade gracefully to whatever is on hand."""

    vendor: str | None = None
    invoice_amount: float | None = None
    invoice_date: date | None = None
    ledger_amount: float | None = None
    ledger_date: date | None = None


def _facts(flag: RawFlag, ctx: InvoiceContext) -> list[str]:
    m = flag.match
    facts = [f"Invoice/receipt ID: {m.document_id}"]
    if ctx.vendor:
        facts.append(f"Vendor: {ctx.vendor}")
    if ctx.invoice_amount is not None:
        facts.append(f"ZATCA receipt amount: {ctx.invoice_amount:.2f} SAR")
    if ctx.invoice_date:
        facts.append(f"Receipt date: {ctx.invoice_date.isoformat()}")

    if flag.signal == "missing_ledger_match":
        facts.append("Finding: no matching transaction exists in the bank ledger.")
    elif flag.signal == "amount_date_mismatch":
        if ctx.ledger_amount is not None:
            facts.append(f"Matched ledger debit: {ctx.ledger_amount:.2f} SAR")
        if ctx.ledger_date:
            facts.append(f"Ledger transaction date: {ctx.ledger_date.isoformat()}")
        facts.append(
            f"Finding: amount differs by {abs(m.amount_delta):.2f} SAR and date "
            f"by {abs(m.date_delta_days)} day(s), beyond tolerance."
        )
    else:  # round_or_repeated_amount
        pattern = []
        if m.is_round_amount:
            pattern.append("a suspiciously round figure")
        if m.is_repeated_amount:
            pattern.append("an amount repeated identically across multiple invoices")
        facts.append(f"Finding: the amount is {' and '.join(pattern)}.")
    return facts


def _fallback_description(flag: RawFlag, ctx: InvoiceContext) -> str:
    """Deterministic template from the same numbers — used whenever the LLM
    call fails. Mirrors the schema_mapping.md Node 2 example phrasing."""
    m = flag.match
    if flag.signal == "amount_date_mismatch" and (
        ctx.invoice_amount is not None and ctx.ledger_amount is not None
    ):
        on_date = f" on {ctx.ledger_date.isoformat()}" if ctx.ledger_date else ""
        return (
            f"ZATCA receipt amount ({ctx.invoice_amount:.2f}) does not match "
            f"ledger debit ({ctx.ledger_amount:.2f}){on_date}."
        )
    if flag.signal == "missing_ledger_match" and ctx.invoice_amount is not None:
        vendor = f" from {ctx.vendor}" if ctx.vendor else ""
        on_date = f" dated {ctx.invoice_date.isoformat()}" if ctx.invoice_date else ""
        return (
            f"Invoice {m.document_id}{vendor} for {ctx.invoice_amount:.2f} SAR"
            f"{on_date} has no matching transaction in the bank ledger."
        )
    if flag.signal == "round_or_repeated_amount" and ctx.invoice_amount is not None:
        return (
            f"Invoice {m.document_id} amount ({ctx.invoice_amount:.2f} SAR) is "
            f"suspiciously round or repeated identically across invoices."
        )
    return default_flag_description(flag)


def write_flag_descriptions(
    raw_flags: list[RawFlag],
    invoice_context: Mapping[str, InvoiceContext],
) -> list[DiscrepancyFlag]:
    """Turns raw flags into DiscrepancyFlags, one per raw flag, in order.

    Severity is copied verbatim from each RawFlag; only `description` comes
    from the model. `invoice_context` maps document_id -> InvoiceContext
    (missing entries just mean less-specific text).
    """
    flags: list[DiscrepancyFlag] = []
    for raw in raw_flags:
        ctx = invoice_context.get(raw.match.document_id, InvoiceContext())
        try:
            description = complete(
                "Write the one-sentence discrepancy description for these facts:\n"
                + "\n".join(f"- {fact}" for fact in _facts(raw, ctx)),
                system=_SYSTEM_PROMPT,
            )
        except LLMError:
            description = _fallback_description(raw, ctx)
        flags.append(DiscrepancyFlag(severity=raw.severity, description=description))
    return flags


__all__ = ["InvoiceContext", "write_flag_descriptions"]
