"""
Saudi Market Oracle node package (architecture.md §1, schema_mapping.md Node 4).

    retrieve.py  pgvector cosine-similarity retrieval over market_knowledge_base
                 (psycopg2 + DATABASE_URL, embeddings via core.llm.embed — the
                 SAME helper the ingest used so vectors match)
    verdict.py   the ONLY LLM call — GPT-5.4 Mini, grounded strictly in the
                 retrieved chunks; sources_cited built deterministically in
                 Python, never by the model

core/graph.py::saudi_market_oracle_node composes these directly (mirrors how
forensic_accountant_node and devils_advocate_node compose their packages) —
this __init__ re-exports the pieces for tests and any future caller.
"""
from __future__ import annotations

from nodes.saudi_market_oracle.retrieve import TOP_K, build_query, retrieve_market_chunks
from nodes.saudi_market_oracle.verdict import (
    AGENCY_DISPLAY,
    assemble_verdict,
    build_sources_cited,
    prettify_citation,
)

__all__ = [
    "TOP_K",
    "build_query",
    "retrieve_market_chunks",
    "AGENCY_DISPLAY",
    "assemble_verdict",
    "build_sources_cited",
    "prettify_citation",
]
