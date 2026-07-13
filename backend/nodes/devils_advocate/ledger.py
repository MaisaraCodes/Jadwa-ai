"""
Devil's Advocate — ledger fetch (architecture.md §1, CONVENTIONS.md rule 3:
mock_open_banking_ledger is read in-node, filtered by cr_number, never
through graph state).

nodes/forensic/matching.py::fetch_ledger_rows already reads this table but
hard-filters to transaction_type='debit' (forensic only ever reconciles
outflow against invoices). Devil's Advocate needs BOTH debit rows (vendor/
cost concentration) and credit rows (revenue volatility), so this is a
devils_advocate-local fetch rather than a shared one — nodes/forensic/
matching.py is left untouched. Same table, same columns, same query shape,
just without the transaction_type filter.
"""
from __future__ import annotations

from typing import Any

from core.supabase import get_service_client

LEDGER_TABLE = "mock_open_banking_ledger"


def fetch_ledger_rows(cr_number: str) -> list[dict[str, Any]]:
    """Queries ALL of the SME's ledger transactions (debit + credit)."""
    response = (
        get_service_client()
        .table(LEDGER_TABLE)
        .select("id, transaction_date, amount, description, transaction_type")
        .eq("cr_number", cr_number)
        .execute()
    )
    return response.data or []


def split_by_type(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (debit_rows, credit_rows)."""
    debit = [row for row in rows if row.get("transaction_type") == "debit"]
    credit = [row for row in rows if row.get("transaction_type") == "credit"]
    return debit, credit


__all__ = ["LEDGER_TABLE", "fetch_ledger_rows", "split_by_type"]
