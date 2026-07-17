"""
Tests for document_intelligence_node (document_intelligence/node.py) and the
vision extractor (document_intelligence/extract.py). No network, no DB: the
vision call and the agent_results UPDATE are monkeypatched out, so these assert
the wiring (extract -> normalize -> DocumentJSON, skip/persist behaviour) in
isolation.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import date

import pytest

from document_intelligence import extract as extract_mod
from document_intelligence import node as node_mod
from document_intelligence.node import document_intelligence_node
from models import ApplicationState, DocumentJSON, SMEProfile, UploadedFile


def _encode_tlv(fields: list[tuple[int, str]]) -> str:
    payload = b""
    for tag, value in fields:
        vb = str(value).encode("utf-8")
        payload += bytes([tag, len(vb)]) + vb
    return base64.b64encode(payload).decode("ascii")


_VALID_QR = _encode_tlv([
    (1, "Gulf Fuel"),
    (2, "300000000000003"),
    (3, "2025-10-12T14:30:00"),
    (4, "1500.50"),
    (5, "195.72"),
])


def _uploaded(document_id: str) -> UploadedFile:
    return UploadedFile(
        document_id=document_id,
        filename=f"{document_id}.jpg",
        storage_url=f"https://storage.example/{document_id}.jpg",
        content_type="image/jpeg",
    )


def _state(*document_ids: str) -> ApplicationState:
    return ApplicationState(
        application_id="app-1",
        status="processing",
        sme_profile=SMEProfile(id="sme-1", company_name="Acme", cr_number="1010", sector="logistics", district="Al-Kharj"),
        raw_documents=[_uploaded(d) for d in document_ids],
        extracted_documents=[],
        forensic_report=None,
        weakness_report=None,
        market_verdict=None,
        risk_baseline=None,
        unified_application_record=None,
    )


@pytest.fixture
def captured_persist(monkeypatch):
    """Replaces the agent_results UPDATE with an in-memory capture."""
    captured: dict = {}

    def fake_persist(application_id, documents):
        captured["application_id"] = application_id
        captured["documents"] = documents

    monkeypatch.setattr(node_mod, "_persist_extracted_documents", fake_persist)
    return captured


class TestDocumentIntelligenceNode:
    def test_extracts_and_normalizes_each_file(self, monkeypatch, captured_persist):
        raw_by_id = {
            "doc-1": {"type": "ZATCA receipt", "vendor": "Gulf Fuel", "extracted_amount": "1,500.50 SAR",
                      "date": "12 Oct 2025", "confidence_score": 0.97},
            "doc-2": {"type": "فاتورة", "vendor": "مؤسسة الخرج", "extracted_amount": "٨٠٠٫٠٠ ريال",
                      "date": "٠٥/١٠/٢٠٢٥", "confidence_score": 0.7},
        }
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: raw_by_id[up.document_id])

        out = document_intelligence_node(_state("doc-1", "doc-2"))
        docs = out["extracted_documents"]

        assert [d.document_id for d in docs] == ["doc-1", "doc-2"]
        assert all(isinstance(d, DocumentJSON) for d in docs)
        assert docs[0].type == "zatca_receipt"
        assert docs[0].extracted_amount == 1500.50
        assert docs[0].date == date(2025, 10, 12)
        assert docs[1].type == "invoice"
        assert docs[1].extracted_amount == 800.0
        assert docs[1].date == date(2025, 10, 5)
        # persisted the same list under the right application_id
        assert captured_persist["application_id"] == "app-1"
        assert captured_persist["documents"] == docs

    def test_zatca_qr_is_decoded_offline_into_verification_hash(self, monkeypatch, captured_persist):
        # A zatca_receipt carrying a valid TLV QR must come out with
        # zatca_verification_hash populated offline (architecture.md §1a) —
        # matching the synthetic_hash(qr, doc_id) ground-truth convention.
        raw = {
            "type": "zatca_receipt", "vendor": "Gulf Fuel", "extracted_amount": 1500.50,
            "date": "2025-10-12", "zatca_qr_base64": _VALID_QR, "confidence_score": 0.95,
        }
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: raw)

        out = document_intelligence_node(_state("doc-qr"))
        doc = out["extracted_documents"][0]

        assert doc.zatca_verification_hash == hashlib.sha256(
            f"{_VALID_QR}|doc-qr".encode("utf-8")
        ).hexdigest()

    def test_document_without_qr_has_no_verification_hash(self, monkeypatch, captured_persist):
        raw = {"type": "invoice", "vendor": "Jarir", "extracted_amount": 300, "date": "2025-10-12"}
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: raw)

        out = document_intelligence_node(_state("doc-noqr"))
        assert out["extracted_documents"][0].zatca_verification_hash is None

    def test_failed_extraction_still_yields_a_low_confidence_document(self, monkeypatch, captured_persist):
        # extract returns {} on any vision/parse failure -> normalize makes a
        # valid, heavily-discounted DocumentJSON; the batch is NOT blocked.
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: {})

        out = document_intelligence_node(_state("doc-empty"))
        docs = out["extracted_documents"]

        assert len(docs) == 1
        assert docs[0].document_id == "doc-empty"
        assert docs[0].extracted_amount == 0.0
        assert docs[0].confidence_score < 0.5

    def test_unvalidatable_document_is_skipped_not_raised(self, monkeypatch, captured_persist):
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: {"amount": 1})
        # Force normalize to reject one specific doc (Pydantic gate returning None).
        real_normalize = node_mod.normalize_extracted_document

        def selective_normalize(raw, document_id):
            if document_id == "doc-bad":
                return None
            return real_normalize(raw, document_id)

        monkeypatch.setattr(node_mod, "normalize_extracted_document", selective_normalize)

        out = document_intelligence_node(_state("doc-ok", "doc-bad"))
        docs = out["extracted_documents"]

        assert [d.document_id for d in docs] == ["doc-ok"]  # bad one dropped, no crash

    def test_no_documents_returns_empty(self, monkeypatch, captured_persist):
        monkeypatch.setattr(node_mod, "extract_document_fields", lambda up: {})
        out = document_intelligence_node(_state())
        assert out["extracted_documents"] == []
        assert captured_persist["documents"] == []


class TestExtractDocumentFields:
    def test_parses_plain_json_reply(self, monkeypatch):
        monkeypatch.setattr(
            extract_mod, "complete_vision",
            lambda *a, **k: '{"type": "invoice", "extracted_amount": 100, "confidence_score": 0.9}',
        )
        raw = extract_mod.extract_document_fields(_uploaded("doc-1"))
        assert raw == {"type": "invoice", "extracted_amount": 100, "confidence_score": 0.9}

    def test_recovers_json_wrapped_in_prose_or_fences(self, monkeypatch):
        monkeypatch.setattr(
            extract_mod, "complete_vision",
            lambda *a, **k: 'Here you go:\n```json\n{"type": "invoice", "vendor": "V"}\n```',
        )
        raw = extract_mod.extract_document_fields(_uploaded("doc-1"))
        assert raw == {"type": "invoice", "vendor": "V"}

    def test_llm_failure_returns_empty_dict(self, monkeypatch):
        def boom(*a, **k):
            raise extract_mod.LLMError("no api key")

        monkeypatch.setattr(extract_mod, "complete_vision", boom)
        assert extract_mod.extract_document_fields(_uploaded("doc-1")) == {}

    def test_unparseable_reply_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(extract_mod, "complete_vision", lambda *a, **k: "sorry, I can't read this")
        assert extract_mod.extract_document_fields(_uploaded("doc-1")) == {}
