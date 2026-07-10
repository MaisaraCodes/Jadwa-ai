"""Document Intelligence Engine (architecture.md §1, Node 1).

`document_intelligence_node` turns raw uploaded files into
`list[DocumentJSON]`. This package holds the pieces of that node:

  * `extract`   — GPT-5.4 vision read: uploaded file -> raw fields dict
  * `normalize` — raw dict -> canonical DocumentJSON (Pydantic-gated)
  * `node`      — the node itself, wiring extract -> normalize per file
"""
from __future__ import annotations

from document_intelligence.extract import extract_document_fields
from document_intelligence.node import document_intelligence_node
from document_intelligence.normalize import normalize_extracted_document

__all__ = [
    "document_intelligence_node",
    "extract_document_fields",
    "normalize_extracted_document",
]
