"""
Forensic accountant — scoring + roll-up layer (architecture.md §1, §1a).

Everything in this module is deterministic Python (CONVENTIONS.md rule 1):
it takes per-invoice match results (produced by the matching step, which
reconciles extracted_documents against mock_open_banking_ledger) and turns
them into severity-graded raw flags and a ForensicReport. No model is called
here — the LLM's only job is the plain-language `description` text on each
DiscrepancyFlag, and that lives in nodes/forensic/explain.py.

The three fraud signals (SYNTHETIC_DATA_SPEC.md):
    1. no matching ledger transaction found          -> "high"
    2. amount/date mismatch beyond tolerance         -> "medium"
    3. suspiciously round or repeated amounts        -> "medium"
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Literal, Mapping

from models import DiscrepancyFlag, ForensicReport, Severity

# Matched amounts may differ from the ledger debit by up to this many SAR.
AMOUNT_TOLERANCE_SAR = 1.00
# Invoice date may differ from the ledger transaction date by up to this many days.
DATE_WINDOW_DAYS = 3
# Amounts at or above this (in SAR) are eligible for the "suspiciously round" signal.
ROUND_AMOUNT_THRESHOLD = 500.00
# An eligible amount counts as suspiciously round when it is an exact multiple of this.
ROUND_AMOUNT_MODULUS_SAR = 100.00
# The same amount appearing on this many (or more) invoices counts as repeated.
REPEATED_AMOUNT_MIN_COUNT = 3

FlagSignal = Literal[
    "missing_ledger_match",
    "amount_date_mismatch",
    "round_or_repeated_amount",
]


@dataclass(frozen=True)
class MatchResult:
    """The interface between the matching step and this scoring layer:
    one per invoice, carrying only what scoring needs to grade it."""

    document_id: str
    matched: bool
    ledger_txn_id: str | None = None
    amount_delta: float = 0.0        # invoice amount − ledger amount (SAR); 0 when unmatched
    date_delta_days: int = 0         # invoice date − ledger date (days); 0 when unmatched
    is_round_amount: bool = False
    is_repeated_amount: bool = False


@dataclass(frozen=True)
class RawFlag:
    """A graded fraud signal on one invoice, before any description text is
    written. Severity is decided HERE and is final — explain.py may only add
    prose, never regrade."""

    signal: FlagSignal
    severity: Severity
    match: MatchResult


def is_suspiciously_round(amount: float) -> bool:
    """Helper for the matching step to populate MatchResult.is_round_amount."""
    return (
        amount >= ROUND_AMOUNT_THRESHOLD
        and round(amount % ROUND_AMOUNT_MODULUS_SAR, 2) in (0.0, ROUND_AMOUNT_MODULUS_SAR)
    )


def repeated_amount_document_ids(amount_by_document: Mapping[str, float]) -> set[str]:
    """Helper for the matching step to populate MatchResult.is_repeated_amount:
    document_ids whose amount appears REPEATED_AMOUNT_MIN_COUNT+ times in the batch."""
    counts = Counter(round(amount, 2) for amount in amount_by_document.values())
    return {
        document_id
        for document_id, amount in amount_by_document.items()
        if counts[round(amount, 2)] >= REPEATED_AMOUNT_MIN_COUNT
    }


def score_invoice(match: MatchResult) -> list[RawFlag]:
    """Grades one invoice against the three fraud signals. Deterministic."""
    flags: list[RawFlag] = []

    if not match.matched:
        flags.append(RawFlag("missing_ledger_match", "high", match))
    elif (
        abs(match.amount_delta) > AMOUNT_TOLERANCE_SAR
        or abs(match.date_delta_days) > DATE_WINDOW_DAYS
    ):
        flags.append(RawFlag("amount_date_mismatch", "medium", match))

    if match.is_round_amount or match.is_repeated_amount:
        flags.append(RawFlag("round_or_repeated_amount", "medium", match))

    return flags


def default_flag_description(flag: RawFlag) -> str:
    """Deterministic description built from MatchResult fields only — used
    when no describer is supplied. explain.py produces richer text from the
    concrete invoice/ledger numbers."""
    m = flag.match
    if flag.signal == "missing_ledger_match":
        return f"No matching bank ledger transaction found for invoice {m.document_id}."
    if flag.signal == "amount_date_mismatch":
        return (
            f"Invoice {m.document_id} differs from ledger transaction "
            f"{m.ledger_txn_id} by {abs(m.amount_delta):.2f} SAR and "
            f"{abs(m.date_delta_days)} day(s), beyond tolerance."
        )
    return (
        f"Invoice {m.document_id} shows a suspiciously round or repeated "
        f"amount pattern."
    )


def build_forensic_report(
    matches: list[MatchResult],
    describe: Callable[[list[RawFlag]], list[DiscrepancyFlag]] | None = None,
) -> ForensicReport:
    """Scores every invoice and rolls the results up into a ForensicReport.

    `describe` turns raw flags into DiscrepancyFlags (the node passes
    explain.write_flag_descriptions); its output severities are overwritten
    with the raw ones so description-writing can never regrade a flag.

    Roll-up: reconciliation_rate = cleanly matched (zero flags) / total;
    any "high" flag -> "red", else any flag -> "yellow", else "green".
    """
    raw_flags: list[RawFlag] = []
    clean_count = 0
    for match in matches:
        invoice_flags = score_invoice(match)
        if not invoice_flags:
            clean_count += 1
        raw_flags.extend(invoice_flags)

    if describe is not None and raw_flags:
        described = describe(raw_flags)
        discrepancy_flags = [
            DiscrepancyFlag(severity=raw.severity, description=flag.description)
            for raw, flag in zip(raw_flags, described)
        ]
    else:
        discrepancy_flags = [
            DiscrepancyFlag(severity=raw.severity, description=default_flag_description(raw))
            for raw in raw_flags
        ]

    if any(flag.severity == "high" for flag in raw_flags):
        overall_status = "red"
    elif raw_flags:
        overall_status = "yellow"
    else:
        overall_status = "green"

    reconciliation_rate = 1.0 if not matches else clean_count / len(matches)

    return ForensicReport(
        overall_status=overall_status,
        reconciliation_rate=reconciliation_rate,
        discrepancy_flags=discrepancy_flags,
    )


__all__ = [
    "AMOUNT_TOLERANCE_SAR",
    "DATE_WINDOW_DAYS",
    "ROUND_AMOUNT_THRESHOLD",
    "ROUND_AMOUNT_MODULUS_SAR",
    "REPEATED_AMOUNT_MIN_COUNT",
    "FlagSignal",
    "MatchResult",
    "RawFlag",
    "is_suspiciously_round",
    "repeated_amount_document_ids",
    "score_invoice",
    "default_flag_description",
    "build_forensic_report",
]
