"""
Tests for the raw-output -> DocumentJSON normalization layer
(document_intelligence/normalize.py). Pure functions, no DB, no LLM: each case
feeds a raw extraction dict and asserts on the resulting DocumentJSON.

Covers the four required scenarios (clean English ZATCA receipt, messy Arabic
handwritten invoice with Arabic-Indic digits, a document missing vendor and
line_items, a malformed amount string) plus the confidence-lowering and
validation-gate contracts.
"""
from __future__ import annotations

from datetime import date

from document_intelligence.normalize import normalize_extracted_document
from models import DocumentJSON


class TestCleanEnglishZatcaReceipt:
    def test_parses_all_fields(self):
        raw = {
            "type": "ZATCA receipt",
            "vendor": "Gulf Fuel Depot",
            "extracted_amount": "1,500.50 SAR",
            "date": "12 Oct 2025",
            "line_items": ["Diesel 500L", "Service fee"],
            "zatca_verification_hash": "abc123xyz",
            "zatca_qr_base64": "AQ5TZWxsZXI=",
            "confidence_score": 0.98,
        }
        doc = normalize_extracted_document(raw, "doc-clean")
        assert isinstance(doc, DocumentJSON)
        assert doc.document_id == "doc-clean"
        assert doc.type == "zatca_receipt"
        assert doc.vendor == "Gulf Fuel Depot"
        assert doc.extracted_amount == 1500.50
        assert doc.currency == "SAR"
        assert doc.date == date(2025, 10, 12)
        assert doc.line_items == ["Diesel 500L", "Service fee"]
        assert doc.zatca_verification_hash == "abc123xyz"
        assert doc.zatca_qr_base64 == "AQ5TZWxsZXI="

    def test_confidence_not_penalized_when_complete(self):
        raw = {
            "type": "zatca_receipt",
            "vendor": "Gulf Fuel Depot",
            "extracted_amount": 1500.50,
            "date": "2025-10-12",
            "confidence_score": 0.98,
        }
        doc = normalize_extracted_document(raw, "doc-1")
        # Nothing had to be defaulted/recovered -> full LLM confidence retained.
        assert doc.confidence_score == 0.98


class TestMessyArabicHandwrittenInvoice:
    def test_arabic_indic_digits_and_currency_word(self):
        raw = {
            "type": "فاتورة",  # invoice
            "vendor": "مؤسسة الخرج للنقل",
            "extracted_amount": "١٬٢٥٠٫٧٥ ريال",  # 1,250.75 riyal in Arabic-Indic digits
            "date": "٠٥/١٠/٢٠٢٥",  # 05/10/2025 -> 5 Oct (dayfirst)
            "confidence_score": 0.7,
        }
        doc = normalize_extracted_document(raw, "doc-ar")
        assert doc.type == "invoice"
        assert doc.vendor == "مؤسسة الخرج للنقل"
        assert doc.extracted_amount == 1250.75
        assert doc.currency == "SAR"
        assert doc.date == date(2025, 10, 5)

    def test_dayfirst_convention(self):
        raw = {"extracted_amount": 10, "date": "05/10/2025", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-df")
        assert doc.date == date(2025, 10, 5)  # 5 October, not 10 May


class TestMissingVendorAndLineItems:
    def test_safe_defaults_and_lowered_confidence(self):
        raw = {
            "type": "invoice",
            "extracted_amount": 800.0,
            "date": "2025-09-01",
            "confidence_score": 0.9,
        }
        doc = normalize_extracted_document(raw, "doc-partial")
        assert doc is not None
        assert doc.vendor is None
        assert doc.line_items == []
        # vendor absence should discount confidence below the stated 0.9.
        assert doc.confidence_score < 0.9


class TestMalformedAmount:
    def test_unparseable_amount_defaults_to_zero_and_penalizes(self):
        raw = {
            "type": "invoice",
            "vendor": "Some Vendor",
            "extracted_amount": "N/A",
            "date": "2025-08-15",
            "confidence_score": 0.95,
        }
        doc = normalize_extracted_document(raw, "doc-bad-amt")
        assert doc is not None  # must NOT crash the batch
        assert doc.extracted_amount == 0.0
        assert doc.confidence_score < 0.95  # heavily discounted

    def test_amount_embedded_in_noise_is_recovered(self):
        raw = {
            "extracted_amount": "total due: 430.00 only",
            "date": "2025-08-15",
            "confidence_score": 0.9,
        }
        doc = normalize_extracted_document(raw, "doc-recover")
        assert doc.extracted_amount == 430.0
        # recovered via fallback -> some discount, but not the full missing penalty.
        assert 0.0 < doc.confidence_score < 0.9


class TestMixedScriptAndBidiControls:
    def test_vendor_strips_bidi_marks_but_keeps_both_scripts(self):
        # A POS receipt with an English brand name embedded in Arabic text,
        # wrapped in LRM/RLM/embedding marks (real artifact from many Saudi
        # receipt printers/OCR pipelines) — must be stripped, not transliterated.
        raw = {
            "type": "invoice",
            "vendor": "‫مطعم‬ ‎STC‎ ‪المحدودة‬",
            "extracted_amount": 45.0,
            "date": "2025-06-01",
            "confidence_score": 0.85,
        }
        doc = normalize_extracted_document(raw, "doc-mixed-vendor")
        assert doc.vendor == "مطعم STC المحدودة"
        assert "‫" not in doc.vendor
        assert "‎" not in doc.vendor

    def test_line_items_strip_bidi_marks(self):
        raw = {
            "extracted_amount": 10.0,
            "date": "2025-06-01",
            "line_items": ["‏Brake Pad Set‏", "فلتر ‪زيت‬"],
            "confidence_score": 0.8,
        }
        doc = normalize_extracted_document(raw, "doc-mixed-items")
        assert doc.line_items == ["Brake Pad Set", "فلتر زيت"]

    def test_mixed_arabic_english_zatca_receipt(self):
        # Arabic ZATCA receipt body with an English vendor brand — realistic
        # for Saudi chains (e.g. a café or hypermarket) printing their Latin
        # brand name inside an otherwise-Arabic receipt.
        raw = {
            "type": "فاتورة ضريبية",  # tax invoice
            "vendor": "بريد‎ Panda ‎المملكة",
            "extracted_amount": "٣٤٫٥٠ ريال",
            "date": "١٥/٠٦/٢٠٢٥",
            "confidence_score": 0.75,
        }
        doc = normalize_extracted_document(raw, "doc-zatca-mixed")
        assert doc.type == "zatca_receipt"
        assert doc.vendor == "بريد Panda المملكة"
        assert doc.extracted_amount == 34.50
        assert doc.currency == "SAR"
        assert doc.date == date(2025, 6, 15)


class TestCurrencyDetection:
    def test_explicit_usd_is_detected(self):
        raw = {"extracted_amount": "$1,200.00", "currency": "USD", "date": "2025-07-01", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-usd")
        assert doc.currency == "USD"
        assert doc.extracted_amount == 1200.0

    def test_defaults_to_sar(self):
        raw = {"extracted_amount": 500, "date": "2025-07-01", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-sar")
        assert doc.currency == "SAR"


class TestTypeMapping:
    def test_unrecognized_type_defaults_to_other_and_penalizes(self):
        raw = {"type": "mystery scroll", "extracted_amount": 10, "date": "2025-07-01", "vendor": "V", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-type")
        assert doc.type == "other"
        assert doc.confidence_score < 0.9

    def test_bank_statement_arabic(self):
        raw = {"type": "كشف حساب", "extracted_amount": 10, "date": "2025-07-01", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-bs")
        assert doc.type == "bank_statement"


class TestValidationGate:
    def test_non_dict_returns_none(self):
        assert normalize_extracted_document(["not", "a", "dict"], "doc-x") is None  # type: ignore[arg-type]

    def test_empty_raw_still_produces_valid_document(self):
        # Everything defaulted: amount 0.0, date today, type other. Valid but
        # very low confidence — the caller can route it to manual review.
        doc = normalize_extracted_document({}, "doc-empty")
        assert isinstance(doc, DocumentJSON)
        assert doc.extracted_amount == 0.0
        assert doc.date == date.today()
        assert doc.confidence_score < 0.5

    def test_missing_date_defaults_to_today(self):
        raw = {"extracted_amount": 100, "vendor": "V", "confidence_score": 0.9}
        doc = normalize_extracted_document(raw, "doc-nodate")
        assert doc.date == date.today()
        assert doc.confidence_score < 0.9
