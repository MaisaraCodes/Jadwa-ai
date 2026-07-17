"""
Saudi Market Oracle — pgvector retrieval (architecture.md §1, schema_mapping.md Node 4).

Pure-Python retrieval over market_knowledge_base: embed a query built from the
SME's sector + district with the SAME core.llm.embed helper the corpus ingest
used (text-embedding-3-large, dimensions=1536 — CONVENTIONS.md "Models &
embeddings"), then run a cosine-similarity search via psycopg2 against
os.environ['DATABASE_URL'] (the Supabase IPv4 Session Pooler, same connection
style as data/ingest_oracle_corpus.py).

The corpus is general regulator reports — `sector` is NULL on every row, so
there is deliberately NO sector WHERE clause; relevance comes purely from
vector similarity. The node stays retrieval-augmented end to end: every
verdict is grounded in and cites what this module retrieves.
"""
from __future__ import annotations

import os
from typing import Any

from core.llm import embed

TABLE = "market_knowledge_base"
TOP_K = 6


def build_query(sector: str | None, district: str | None) -> str:
    """Deterministic natural-language retrieval query from profile fields."""
    parts = []
    if sector:
        parts.append(f"Saudi Arabia SME market outlook and trends for the {sector} sector")
    if district:
        parts.append(f"business activity and market saturation in {district}")
    if not parts:
        parts.append("Saudi Arabia SME market outlook and sector trends")
    return "; ".join(parts)


def retrieve_market_chunks(
    sector: str | None,
    district: str | None,
    *,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Returns the top-k most similar corpus chunks as dicts:
    {content, source_agency, citation, score}.

    Raises whatever embed()/psycopg2 raise — the caller (the node) catches
    and falls back; retrieval itself stays honest and never fabricates rows.
    """
    import psycopg2

    query = build_query(sector, district)
    query_embedding = embed([query])[0]
    # Same pgvector literal format the ingest used.
    vector_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT content, source_agency, citation,
                       1 - (embedding <=> %s::vector) AS score
                FROM {TABLE}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vector_literal, vector_literal, top_k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"content": r[0], "source_agency": r[1], "citation": r[2], "score": float(r[3])}
        for r in rows
    ]


__all__ = ["TABLE", "TOP_K", "build_query", "retrieve_market_chunks"]
