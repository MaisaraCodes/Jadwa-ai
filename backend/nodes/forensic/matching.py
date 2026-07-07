"""
Forensic accountant — invoice/ledger matching step (architecture.md §1, §1a).

Reads mock_open_banking_ledger from Postgres, filtered by the SME's
cr_number, and reconciled against extracted_documents (CONVENTIONS.md rule
3: the ledger is queried in-node — it never travels through graph state).
Produces one MatchResult (nodes/forensic/scoring.py) per document, which
scoring.py then grades into fraud flags.

Pure logic (`match_documents_to_ledger`) takes plain ledger rows so it can
be unit-tested without a database; `fetch_ledger_rows` is the one function
that touches Postgres.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from core.supabase import get_service_client
from models import DocumentJSON
from nodes.forensic.explain import InvoiceContext
from nodes.forensic.scoring import (
    MatchResult,
    is_suspiciously_round,
    repeated_amount_document_ids,
)

LEDGER_TABLE = "mock_open_banking_ledger"

# How far a candidate ledger debit may be from the invoice date (either
# direction) before it stops counting as a candidate at all. Wider than
# scoring.DATE_WINDOW_DAYS on purpose: a late-posted but real payment should
# still be FOUND (and then graded on its own delta) rather than reported as
# "no matching transaction" (fraud signal 1 is for genuinely absent debits).
MAX_SEARCH_WINDOW_DAYS = 30


def fetch_ledger_rows(cr_number: str) -> list[dict[str, Any]]:
    """Queries the SME's debit transactions from mock_open_banking_ledger."""
    response = (
        get_service_client()
        .table(LEDGER_TABLE)
        .select("id, transaction_date, amount, description")
        .eq("cr_number", cr_number)
        .eq("transaction_type", "debit")
        .execute()
    )
    return response.data or []


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def match_documents_to_ledger(
    documents: list[DocumentJSON],
    ledger_rows: list[dict[str, Any]],
) -> tuple[list[MatchResult], dict[str, InvoiceContext]]:
    """Greedily pairs each document with its closest not-yet-claimed ledger
    debit (by date distance, then amount distance) within
    MAX_SEARCH_WINDOW_DAYS. Each ledger row can satisfy at most one
    document, so two identical invoices can't both point at one payment.

    Returns (matches, invoice_context) — the latter carries the concrete
    vendor/amount/date figures explain.py needs to write specific text.
    """
    candidates = [
        {
            "id": row.get("id"),
            "date": _parse_date(row["transaction_date"]),
            "amount": abs(float(row["amount"])),
        }
        for row in ledger_rows
    ]
    claimed = [False] * len(candidates)

    amount_by_document = {doc.document_id: doc.extracted_amount for doc in documents}
    repeated_ids = repeated_amount_document_ids(amount_by_document)

    matches: list[MatchResult] = []
    invoice_context: dict[str, InvoiceContext] = {}

    for doc in documents:
        round_amount = is_suspiciously_round(doc.extracted_amount)
        repeated_amount = doc.document_id in repeated_ids

        best_idx: int | None = None
        best_score: tuple[int, float] | None = None
        for idx, candidate in enumerate(candidates):
            if claimed[idx]:
                continue
            day_delta = abs((doc.date - candidate["date"]).days)
            if day_delta > MAX_SEARCH_WINDOW_DAYS:
                continue
            amount_delta = abs(doc.extracted_amount - candidate["amount"])
            score = (day_delta, amount_delta)
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx

        if best_idx is None:
            matches.append(MatchResult(
                document_id=doc.document_id,
                matched=False,
                is_round_amount=round_amount,
                is_repeated_amount=repeated_amount,
            ))
            invoice_context[doc.document_id] = InvoiceContext(
                vendor=doc.vendor, invoice_amount=doc.extracted_amount, invoice_date=doc.date,
            )
            continue

        claimed[best_idx] = True
        candidate = candidates[best_idx]
        matches.append(MatchResult(
            document_id=doc.document_id,
            matched=True,
            ledger_txn_id=str(candidate["id"]) if candidate["id"] is not None else None,
            amount_delta=doc.extracted_amount - candidate["amount"],
            date_delta_days=(doc.date - candidate["date"]).days,
            is_round_amount=round_amount,
            is_repeated_amount=repeated_amount,
        ))
        invoice_context[doc.document_id] = InvoiceContext(
            vendor=doc.vendor,
            invoice_amount=doc.extracted_amount,
            invoice_date=doc.date,
            ledger_amount=candidate["amount"],
            ledger_date=candidate["date"],
        )

    return matches, invoice_context


def reconcile_against_ledger(
    cr_number: str, documents: list[DocumentJSON]
) -> tuple[list[MatchResult], dict[str, InvoiceContext]]:
    """Convenience wrapper: fetch + match in one call, for node code."""
    ledger_rows = fetch_ledger_rows(cr_number)
    return match_documents_to_ledger(documents, ledger_rows)


__all__ = [
    "LEDGER_TABLE",
    "MAX_SEARCH_WINDOW_DAYS",
    "fetch_ledger_rows",
    "match_documents_to_ledger",
    "reconcile_against_ledger",
]
