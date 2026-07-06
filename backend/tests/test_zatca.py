"""
Tests for core/zatca.py (offline ZATCA Phase-2 QR parser) and its wiring into
forensic_accountant_node (core/graph.py).
"""
from __future__ import annotations

import base64
from datetime import date
from decimal import Decimal

import pytest

from core.graph import forensic_accountant_node
from core.zatca import ZatcaParseError, ZatcaQRParser
from models import DocumentJSON, SMEProfile


def encode_tlv(fields: list[tuple[int, str]]) -> str:
    payload = b""
    for tag, value in fields:
        vb = value.encode("utf-8")
        payload += bytes([tag, len(vb)]) + vb
    return base64.b64encode(payload).decode("ascii")


def make_qr(
    seller="Gulf Fuel Depot",
    vat_number="300000000000003",
    timestamp="2025-10-12T14:30:00",
    total="1500.50",
    vat="195.50",
) -> str:
    return encode_tlv([
        (1, seller),
        (2, vat_number),
        (3, timestamp),
        (4, total),
        (5, vat),
    ])


# ---------------------------------------------------------------------------
# ZatcaQRParser.parse() / validate_against_ledger()
# ---------------------------------------------------------------------------
class TestZatcaQRParser:
    def test_happy_path(self):
        qr = make_qr()
        data = ZatcaQRParser(qr).parse()
        assert data.seller_name == "Gulf Fuel Depot"
        assert data.vat_number == "300000000000003"
        assert data.timestamp == "2025-10-12T14:30:00"
        assert data.invoice_total == Decimal("1500.50")
        assert data.vat_total == Decimal("195.50")
        assert data.missing_required_fields() == []

    def test_ledger_mismatch(self):
        qr = make_qr(total="1500.50")
        parser = ZatcaQRParser(qr)
        result = parser.validate_against_ledger({
            "seller_name": "Gulf Fuel Depot",
            "invoice_total": "999.00",
        })
        assert result.is_valid is False
        assert "invoice_total" in result.mismatches
        assert result.mismatches["invoice_total"] == (Decimal("1500.50"), "999.00")

    def test_ledger_match_within_tolerance(self):
        qr = make_qr(total="1500.50")
        parser = ZatcaQRParser(qr)
        result = parser.validate_against_ledger({"invoice_total": "1500.51"})
        assert result.is_valid is True
        assert result.mismatches == {}

    def test_malformed_tlv_bad_length_byte(self):
        # Tag 1 declares a length longer than the remaining bytes.
        payload = bytes([1, 200]) + b"short"
        bad_qr = base64.b64encode(payload).decode("ascii")
        with pytest.raises(ZatcaParseError, match="declares length"):
            ZatcaQRParser(bad_qr).parse()

    def test_invalid_base64(self):
        with pytest.raises(ZatcaParseError, match="Invalid base64"):
            ZatcaQRParser("not-valid-base64!!!").parse()

    def test_truncated_required_field(self):
        # Only tags 1-3 present; tags 4 (invoice_total) and 5 (vat_total) missing.
        qr = encode_tlv([
            (1, "Gulf Fuel Depot"),
            (2, "300000000000003"),
            (3, "2025-10-12T14:30:00"),
        ])
        with pytest.raises(ZatcaParseError, match="missing required tag"):
            ZatcaQRParser(qr).parse()

    def test_empty_qr_string_raises_on_construction(self):
        with pytest.raises(ZatcaParseError):
            ZatcaQRParser("")


# ---------------------------------------------------------------------------
# forensic_accountant_node integration
# ---------------------------------------------------------------------------
def make_sme_profile() -> SMEProfile:
    return SMEProfile(
        id="sme-1", company_name="Acme SME", cr_number="1010101010",
        sector="logistics", district="Al-Kharj",
    )


class TestForensicAccountantZatcaIntegration:
    def test_matching_qr_and_document_is_green(self):
        doc = DocumentJSON(
            document_id="doc-1", type="zatca_receipt", vendor="Gulf Fuel Depot",
            extracted_amount=1500.50, date=date(2025, 10, 12), confidence_score=0.95,
            zatca_qr_base64=make_qr(seller="Gulf Fuel Depot", total="1500.50"),
        )
        state = {
            "application_id": "app-1", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": [doc],
        }
        result = forensic_accountant_node(state)
        report = result["forensic_report"]
        assert report.overall_status == "green"
        assert report.discrepancy_flags == []
        assert report.reconciliation_rate == 1.0

    def test_qr_amount_mismatch_flags_red(self):
        doc = DocumentJSON(
            document_id="doc-2", type="zatca_receipt", vendor="Gulf Fuel Depot",
            extracted_amount=999.00, date=date(2025, 10, 12), confidence_score=0.95,
            zatca_qr_base64=make_qr(seller="Gulf Fuel Depot", total="1500.50"),
        )
        state = {
            "application_id": "app-2", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": [doc],
        }
        result = forensic_accountant_node(state)
        report = result["forensic_report"]
        assert report.overall_status == "red"
        assert len(report.discrepancy_flags) == 1
        assert report.discrepancy_flags[0].severity == "high"
        assert "doc-2" in report.discrepancy_flags[0].description
        assert report.reconciliation_rate == 0.0

    def test_unparseable_qr_flags_medium_not_crash(self):
        doc = DocumentJSON(
            document_id="doc-3", type="zatca_receipt", vendor="Gulf Fuel Depot",
            extracted_amount=500.00, date=date(2025, 10, 12), confidence_score=0.95,
            zatca_qr_base64="not-valid-base64!!!",
        )
        state = {
            "application_id": "app-3", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": [doc],
        }
        result = forensic_accountant_node(state)
        report = result["forensic_report"]
        assert report.overall_status == "yellow"
        assert len(report.discrepancy_flags) == 1
        assert report.discrepancy_flags[0].severity == "medium"
        assert "invalid base64" in report.discrepancy_flags[0].description.lower()

    def test_document_without_qr_is_ignored(self):
        doc = DocumentJSON(
            document_id="doc-4", type="invoice", vendor="Some Vendor",
            extracted_amount=200.00, date=date(2025, 10, 12), confidence_score=0.9,
            zatca_qr_base64=None,
        )
        state = {
            "application_id": "app-4", "sme_profile": make_sme_profile(),
            "raw_documents": [], "extracted_documents": [doc],
        }
        result = forensic_accountant_node(state)
        report = result["forensic_report"]
        assert report.overall_status == "green"
        assert report.discrepancy_flags == []
        assert report.reconciliation_rate == 1.0
