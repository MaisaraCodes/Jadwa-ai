"""
Pure-Python tests for the ledger-matching step (nodes/forensic/matching.py).
No DB: match_documents_to_ledger takes plain ledger row dicts, mirroring
what fetch_ledger_rows returns from mock_open_banking_ledger.
"""
from __future__ import annotations

from datetime import date, timedelta

from models import DocumentJSON
from nodes.forensic.matching import MAX_SEARCH_WINDOW_DAYS, match_documents_to_ledger


def make_doc(document_id: str, amount: float, when: date, vendor: str = "Gulf Fuel Depot") -> DocumentJSON:
    return DocumentJSON(
        document_id=document_id, type="invoice", vendor=vendor,
        extracted_amount=amount, date=when, confidence_score=0.95,
    )


def ledger_row(txn_id: str, amount: float, when: date, description: str = "Supplier payment") -> dict:
    return {"id": txn_id, "transaction_date": when.isoformat(), "amount": -amount, "description": description}


class TestMatchDocumentsToLedger:
    def test_clean_match(self):
        doc = make_doc("doc-1", 1500.50, date(2025, 10, 12))
        matches, ctx = match_documents_to_ledger([doc], [ledger_row("txn-1", 1500.50, date(2025, 10, 12))])
        assert len(matches) == 1
        m = matches[0]
        assert m.matched is True
        assert m.ledger_txn_id == "txn-1"
        assert m.amount_delta == 0.0
        assert m.date_delta_days == 0
        assert ctx["doc-1"].ledger_amount == 1500.50
        assert ctx["doc-1"].ledger_date == date(2025, 10, 12)

    def test_no_candidate_within_window_is_unmatched(self):
        doc = make_doc("doc-fab", 9000.00, date(2025, 11, 3))
        far_row = ledger_row("txn-x", 9000.00, date(2025, 11, 3) - timedelta(days=MAX_SEARCH_WINDOW_DAYS + 5))
        matches, ctx = match_documents_to_ledger([doc], [far_row])
        assert matches[0].matched is False
        assert matches[0].ledger_txn_id is None
        assert ctx["doc-fab"].invoice_amount == 9000.00

    def test_empty_ledger_is_unmatched(self):
        doc = make_doc("doc-fab", 9000.00, date(2025, 11, 3))
        matches, _ = match_documents_to_ledger([doc], [])
        assert matches[0].matched is False

    def test_amount_mismatch_within_window_is_matched_with_delta(self):
        doc = make_doc("doc-2", 5000.00, date(2025, 9, 1))
        matches, ctx = match_documents_to_ledger([doc], [ledger_row("txn-2", 4500.00, date(2025, 9, 2))])
        m = matches[0]
        assert m.matched is True
        assert m.amount_delta == 500.00
        assert m.date_delta_days == -1
        assert ctx["doc-2"].ledger_amount == 4500.00

    def test_two_docs_do_not_claim_the_same_ledger_row(self):
        docs = [make_doc("doc-a", 1000.00, date(2025, 6, 1)), make_doc("doc-b", 1000.00, date(2025, 6, 2))]
        rows = [ledger_row("txn-only", 1000.00, date(2025, 6, 1))]
        matches, _ = match_documents_to_ledger(docs, rows)
        matched_flags = [m.matched for m in matches]
        assert matched_flags.count(True) == 1
        assert matched_flags.count(False) == 1

    def test_closest_candidate_by_date_then_amount_is_chosen(self):
        doc = make_doc("doc-c", 2000.00, date(2025, 5, 15))
        rows = [
            ledger_row("txn-far-exact", 2000.00, date(2025, 5, 1)),
            ledger_row("txn-near-off", 1990.00, date(2025, 5, 16)),
        ]
        matches, _ = match_documents_to_ledger([doc], rows)
        assert matches[0].ledger_txn_id == "txn-near-off"

    def test_round_and_repeated_flags_populated_even_when_unmatched(self):
        docs = [make_doc(f"doc-{i}", 5000.00, date(2025, 3, i + 1)) for i in range(3)]
        matches, _ = match_documents_to_ledger(docs, [])
        assert all(m.is_round_amount for m in matches)
        assert all(m.is_repeated_amount for m in matches)
