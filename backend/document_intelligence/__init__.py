"""Document Intelligence Engine (architecture.md §1, Node 1).

`document_intelligence_node` turns raw uploaded files into
`list[DocumentJSON]`. This package holds the pieces of that node:

  * `extract`      — GPT-5.4 vision read: uploaded file -> raw fields dict
  * `normalize`    — raw dict -> canonical DocumentJSON (Pydantic-gated)
  * `zatca_enrich` — offline ZATCA TLV QR decode -> zatca_verification_hash
  * `node`         — the node itself, wiring extract -> normalize -> enrich per file
"""
from __future__ import annotations

from document_intelligence.extract import extract_document_fields
from document_intelligence.node import document_intelligence_node
from document_intelligence.normalize import normalize_extracted_document
from document_intelligence.zatca_enrich import enrich_with_zatca

__all__ = [
    "document_intelligence_node",
    "extract_document_fields",
    "normalize_extracted_document",
    "enrich_with_zatca",
]
