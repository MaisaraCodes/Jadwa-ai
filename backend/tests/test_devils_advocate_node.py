"""
Node test for devils_advocate_node (core/graph.py) — mirrors
tests/test_zatca.py's TestForensicAccountantZatcaIntegration pattern:
monkeypatch the ledger fetch and the LLM narrator so this stays DB-free and
LLM-free, then assert the node writes ONLY weakness_report and produces a
valid WeaknessReport.
"""
from __future__ import annotations

from datetime import date

import pytest

import core.graph as graph_module
import nodes.devils_advocate.narrate as narrate_module
from core.graph import devils_advocate_node
from models import DocumentJSON, SMEProfile, WeaknessReport


def make_sme_profile(**overrides) -> SMEProfile:
    defaults = dict(
        id="sme-1", company_name="Rawad Logistics", cr_number="1010482913",
        sector="logistics", district="Al-Kharj",
    )
    defaults.update(overrides)
    return SMEProfile(**defaults)


def make_doc(document_id: str, vendor: str, amount: float, when: date) -> DocumentJSON:
    return DocumentJSON(
        document_id=document_id, type="invoice", vendor=vendor,
        extracted_amount=amount, date=when, confidence_score=0.95,
    )


def debit_row(amount: float, when: str, counterparty: str, description: str = "Recurring cost") -> dict:
    return {
        "id": "d", "transaction_date": when, "amount": -amount,
        "description": f"{description} — {counterparty}", "transaction_type": "debit",
    }


def credit_row(amount: float, when: str) -> dict:
    return {
        "id": "c", "transaction_date": when, "amount": amount,
        "description": "Monthly revenue — Customer receipts", "transaction_type": "credit",
    }


class TestDevilsAdvocateNode:
    @pytest.fixture(autouse=True)
    def no_llm(self, monkeypatch):
        def boom(*args, **kwargs):
            raise narrate_module.LLMError("forced failure for test")

        monkeypatch.setattr(narrate_module, "complete_full", boom)

    def test_writes_only_weakness_report_and_produces_valid_report(self, monkeypatch):
        ledger_rows = (
            [debit_row(90_000, f"2025-{m:02d}-05", "ADNOC Fuel", "Recurring fuel") for m in range(1, 7)]
            + [credit_row(100_000 + m * 40_000, f"2025-{m:02d}-03") for m in range(1, 7)]
        )
        monkeypatch.setattr(graph_module, "fetch_devils_advocate_ledger_rows", lambda cr_number: ledger_rows)

        docs = [make_doc("doc-1", "ADNOC Fuel", 5000.0, date(2025, 6, 1))]
        state = {
            "application_id": "app-1", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": docs,
        }
        result = devils_advocate_node(state)

        assert set(result.keys()) == {"weakness_report"}
        report = result["weakness_report"]
        assert isinstance(report, WeaknessReport)
        assert 0 <= report.business_model_score <= 100
        assert len(report.critical_weaknesses) == len(report.mitigation_suggestions)
        assert len(report.critical_weaknesses) > 0  # this fixture is designed to trigger signals
        # Persist contract: round-trips through model_dump(mode="json").
        assert WeaknessReport.model_validate(report.model_dump(mode="json")) == report

    def test_handles_empty_ledger_and_documents_without_crashing(self, monkeypatch):
        monkeypatch.setattr(graph_module, "fetch_devils_advocate_ledger_rows", lambda cr_number: [])
        state = {
            "application_id": "app-2", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": [],
        }
        result = devils_advocate_node(state)

        assert set(result.keys()) == {"weakness_report"}
        report = result["weakness_report"]
        assert report.business_model_score == 100
        assert report.critical_weaknesses == []
        assert report.mitigation_suggestions == []

    def test_llm_failure_falls_back_to_deterministic_text_not_a_crash(self, monkeypatch):
        # no_llm fixture already forces every complete_full call to raise;
        # this just asserts the node still produces usable text instead of
        # propagating the failure.
        ledger_rows = [debit_row(50_000, f"2025-{m:02d}-05", "Saudi Diesel") for m in range(1, 4)]
        monkeypatch.setattr(graph_module, "fetch_devils_advocate_ledger_rows", lambda cr_number: ledger_rows)
        docs = [make_doc("doc-1", "Saudi Diesel", 4000.0, date(2025, 3, 1))]
        state = {
            "application_id": "app-3", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": docs,
        }
        report = devils_advocate_node(state)["weakness_report"]
        assert all(isinstance(w, str) and w for w in report.critical_weaknesses)
        assert all(isinstance(m, str) and m for m in report.mitigation_suggestions)
