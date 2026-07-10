"""
Tests for document_intelligence/zatca_enrich.py — the offline ZATCA TLV QR
decode that populates zatca_verification_hash (architecture.md §1a). No network,
no DB, no LLM: enrichment is pure offline decode of a Base64 TLV payload.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import date

from document_intelligence.zatca_enrich import enrich_with_zatca
from models import DocumentJSON


def _encode_tlv(fields: list[tuple[int, str]]) -> str:
    """Builds a Base64 ZATCA TLV payload, matching the synthetic generator's
    encode_zatca_tlv (tag byte + length byte + UTF-8 value per field)."""
    payload = b""
    for tag, value in fields:
        vb = str(value).encode("utf-8")
        payload += bytes([tag, len(vb)]) + vb
    return base64.b64encode(payload).decode("ascii")


# A well-formed Phase-2 *simplified* QR: tags 1-5 only (no tag-6 hash), exactly
# like data/generate_synthetic_data.py emits. Seller name is Arabic to exercise
# UTF-8 multi-byte handling in the parser.
_VALID_QR = _encode_tlv([
    (1, "مؤسسة الخرج للنقل"),
    (2, "300000000000003"),
    (3, "2025-10-12T14:30:00"),
    (4, "1500.50"),
    (5, "195.72"),
])


def _doc(document_id: str, *, qr: str | None, confidence: float = 0.9) -> DocumentJSON:
    return DocumentJSON(
        document_id=document_id,
        type="zatca_receipt",
        vendor="Gulf Fuel",
        extracted_amount=1500.50,
        currency="SAR",
        date=date(2025, 10, 12),
        zatca_qr_base64=qr,
        confidence_score=confidence,
    )


class TestEnrichWithZatca:
    def test_valid_qr_populates_verification_hash(self):
        doc = _doc("doc-1", qr=_VALID_QR)
        out = enrich_with_zatca(doc)

        expected = hashlib.sha256(f"{_VALID_QR}|doc-1".encode("utf-8")).hexdigest()
        assert out.zatca_verification_hash == expected
        assert out.confidence_score == 0.9  # untouched on success

    def test_hash_matches_synthetic_generator_convention(self):
        # The offline hash must equal the ground-truth synthetic_hash(qr, doc_id)
        # so document intelligence output agrees with the seeded demo data.
        doc = _doc("abc-123", qr=_VALID_QR)
        out = enrich_with_zatca(doc)
        assert out.zatca_verification_hash == hashlib.sha256(
            f"{_VALID_QR}|abc-123".encode("utf-8")
        ).hexdigest()

    def test_no_qr_is_returned_unchanged(self):
        doc = _doc("doc-2", qr=None)
        out = enrich_with_zatca(doc)
        assert out.zatca_verification_hash is None
        assert out.confidence_score == 0.9

    def test_empty_qr_string_is_treated_as_no_qr(self):
        out = enrich_with_zatca(_doc("doc-3", qr="   "))
        assert out.zatca_verification_hash is None
        assert out.confidence_score == 0.9

    def test_invalid_base64_flags_without_crashing(self):
        # QR present but not decodable -> hash stays None, confidence lowered.
        doc = _doc("doc-4", qr="!!!not base64!!!", confidence=0.9)
        out = enrich_with_zatca(doc)
        assert out.zatca_verification_hash is None
        assert out.confidence_score < 0.9

    def test_valid_base64_but_malformed_tlv_flags_without_crashing(self):
        # Base64 that decodes but whose TLV is missing required tags 1-5.
        partial = _encode_tlv([(1, "Only a seller name, no other tags")])
        doc = _doc("doc-5", qr=partial, confidence=0.8)
        out = enrich_with_zatca(doc)
        assert out.zatca_verification_hash is None
        assert out.confidence_score < 0.8

    def test_truncated_tlv_declared_length_overruns_buffer(self):
        # Tag 1 claims length 99 but far fewer bytes follow -> ZatcaParseError.
        payload = bytes([1, 99]) + b"short"
        qr = base64.b64encode(payload).decode("ascii")
        out = enrich_with_zatca(_doc("doc-6", qr=qr))
        assert out.zatca_verification_hash is None
        assert out.confidence_score < 0.9
