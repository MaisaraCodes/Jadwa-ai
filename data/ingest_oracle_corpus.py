"""
ingest_oracle_corpus.py — Jadwa.ai Saudi Market Oracle corpus ingestion
(Phase 3, Node 4 prep — schema_mapping.md §3 `market_knowledge_base`).

Chunks + embeds the local Arabic corpus in data/oracle_corpus/<Agency>/*.pdf into
the live `market_knowledge_base` pgvector table. This is retrieval-augmented
grounding for the saudi_market_oracle_node (architecture.md §1): the node
EMBEDS and RETRIEVES this material at query time — it is never "trained on" it.

Standalone and separate from generate_synthetic_data.py; does not touch any
table that script owns (sme_profiles, applications, mock_open_banking_ledger,
agent_results).

Run:  python data/ingest_oracle_corpus.py           (idempotent — safe to re-run)

Env (backend/.env): OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS,
                     DATABASE_URL
Deps: psycopg2-binary, pymupdf, tiktoken, python-dotenv (see backend/requirements.txt)

--------------------------------------------------------------------------------
CONFIRMED LIVE SCHEMA — introspected 2026-07-16 against the live Supabase project.
Direct Postgres (DATABASE_URL) could not be reached from the introspecting
sandbox: `db.<ref>.supabase.co` resolves to an AAAA-only record and the sandbox
has no IPv6 egress (confirmed via `Resolve-DnsName` + a raw TCP test to the
resolved address). Schema was instead confirmed via SUPABASE_URL's PostgREST
OpenAPI document (GET {SUPABASE_URL}/rest/v1/), which mirrors
information_schema exactly for column names/types:

    market_knowledge_base
      id         uuid                  primary key, default extensions.uuid_generate_v4()
      sector     text                  nullable
      content    text                  not null
      embedding  public.vector(1536)   nullable

  -> Vector column confirmed 1536-dim. Matches the approved
     text-embedding-3-large + dimensions=1536 config. Proceeding (no STOP).

  Indexes: NOT determined. The REST/OpenAPI introspection path used here
  does not expose pg_indexes/pg_indexes-equivalent info, and direct SQL
  access was unavailable in this environment. Confirm via the Supabase SQL
  editor (`select * from pg_indexes where tablename = 'market_knowledge_base'`)
  before assuming an ivfflat/hnsw index exists on `embedding`.

  SCHEMA GAP vs. this task's original brief — read before writing the
  retrieval node:
    This table has NO dedicated column for source agency, source filename,
    or citation label, and NO `district` column. Two decisions were made to
    fit the ACTUAL columns rather than guessing new ones into existence:

    1. `content` stores a JSON string (not raw prose):
           {"text": "<clean chunk>", "source_agency": "SAMA",
            "source_filename": "sama_sme_report_q3_2025.pdf",
            "citation": "SAMA — Sama Sme Report Q3 2025"}
       The retrieval node MUST `json.loads(row["content"])` and read
       `["text"]` for the passage, `["citation"]` for `MarketVerdict.sources_cited`.
       The embedding is computed from ONLY the clean chunk text (before the
       JSON payload is built) — no metadata noise in the vector.
    2. `sector` is left NULL for every row this script writes. These PDFs
       are general regulator/agency reports (SAMA, GASTAT, ...), not tied to
       one SME business sector, and architecture.md implies `sector` is
       reserved for filtering by `sme_profile.sector` (values like
       "logistics"/"cafe"/"retail"). Writing an agency name into `sector`
       would silently break that future filter. Flag this to whoever builds
       the retrieval query before they lean on sector-column filtering —
       right now similarity search must be purely on `embedding`.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
BACKEND_DIR = DATA_DIR.parents[0] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

import fitz  # PyMuPDF  # noqa: E402
import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402
import tiktoken  # noqa: E402

from core.llm import LLMError, embed  # noqa: E402

# =====================================================================================
# CONFIG — knobs
# =====================================================================================
CORPUS_DIR = DATA_DIR / "oracle_corpus"
TABLE = "market_knowledge_base"

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMS = 1536
CHUNK_SIZE = 400          # tokens per chunk (cl100k_base)
CHUNK_OVERLAP = 60        # tokens carried into the next chunk for continuity
BATCH_SIZE = 64           # texts per embeddings API call
MIN_EXTRACT_CHARS = 40    # below this, treat the PDF as image-only/unextractable

# Fixed namespace so chunk ids are stable across runs/machines (uuid5 is
# deterministic given the same namespace + name -> re-running never duplicates).
ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "jadwa.ai/oracle_corpus")

# Source subfolders (exact names in data/oracle_corpus/) -> display label used
# in citations. Matched case-insensitively against actual directory names.
SOURCE_FOLDERS = ["Sama", "Monshaat", "Gastat", "Kafalah", "Simah", "Moc", "hrsd", "fsdp"]
AGENCY_LABEL = {
    "sama": "SAMA",
    "monshaat": "Monsha'at",
    "gastat": "GASTAT",
    "kafalah": "Kafalah",
    "simah": "SIMAH",
    "moc": "MoC",
    "hrsd": "HRSD",
    "fsdp": "FSDP",
}

SCHEMA_REPORT = """\
market_knowledge_base (confirmed live schema, 2026-07-16):
  id         uuid                  primary key, default extensions.uuid_generate_v4()
  sector     text                  nullable  (left NULL by this script — see file header)
  content    text                  not null  (JSON: text/source_agency/source_filename/citation)
  embedding  public.vector(1536)   nullable  -- CONFIRMED 1536-dim

Indexes: not determined (no direct SQL access when this was introspected;
check pg_indexes on market_knowledge_base before assuming ivfflat/hnsw exists).
"""

_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?؟۔])\s+")


# =====================================================================================
# Chunking — Arabic-aware (paragraph, then sentence, boundaries), token-budgeted
# =====================================================================================
def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARA_SPLIT_RE.split(text) if p.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]
    return sentences or [paragraph]


def chunk_text(text: str, encoding, *, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Greedily packs sentences (grouped by paragraph) into token-budgeted
    chunks, carrying ~`overlap` tokens of trailing context into the next chunk."""
    sentences: list[str] = []
    for para in _split_paragraphs(text):
        sentences.extend(_split_sentences(para))
    if not sentences:
        return []

    token_counts = [len(encoding.encode(s)) for s in sentences]
    n = len(sentences)
    chunks: list[str] = []
    start = 0
    while start < n:
        end = start
        total = 0
        while end < n and (total + token_counts[end] <= chunk_size or end == start):
            total += token_counts[end]
            end += 1
        chunk = " ".join(sentences[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        new_start = end
        back_total = 0
        while new_start > start and back_total < overlap:
            new_start -= 1
            back_total += token_counts[new_start]
        start = max(new_start, start + 1)  # guarantee forward progress
    return chunks


# =====================================================================================
# PDF extraction
# =====================================================================================
def extract_pdf_text(path: Path) -> str:
    doc = fitz.open(path)
    try:
        pages = [page.get_text("text") for page in doc]
    finally:
        doc.close()
    return "\n\n".join(p.strip() for p in pages if p and p.strip())


def citation_label(agency: str, filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    title = " ".join(w.capitalize() if w.isascii() else w for w in stem.split())
    return f"{agency} — {title}"


def chunk_id_for(relative_path: str, index: int) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, f"{relative_path}::{index}"))


# =====================================================================================
# DB
# =====================================================================================
def to_vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def upsert_batch(cur, rows: list[dict]) -> None:
    """rows: id, sector(None), content(json str), embedding(vector literal)."""
    values = [(r["id"], r["sector"], r["content"], r["embedding"]) for r in rows]
    psycopg2.extras.execute_values(
        cur,
        f"INSERT INTO {TABLE} (id, sector, content, embedding) VALUES %s "
        f"ON CONFLICT (id) DO UPDATE SET "
        f"content = EXCLUDED.content, embedding = EXCLUDED.embedding, sector = EXCLUDED.sector",
        values,
        template="(%s, %s, %s, %s::vector)",
    )


# =====================================================================================
# Main
# =====================================================================================
def main() -> None:
    print(SCHEMA_REPORT)

    if not CORPUS_DIR.exists():
        print(f"ERROR: corpus directory not found: {CORPUS_DIR}")
        print("Nothing to ingest. Create data/oracle_corpus/<Agency>/*.pdf and re-run.")
        return

    try:
        encoding = tiktoken.encoding_for_model(EMBED_MODEL)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    existing_folders = {p.name.lower(): p for p in CORPUS_DIR.iterdir() if p.is_dir()}

    files_processed = 0
    files_skipped: list[tuple[str, str]] = []
    chunks_per_source: dict[str, int] = {label: 0 for label in AGENCY_LABEL.values()}
    pending: list[dict] = []

    dsn = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    def flush_pending() -> None:
        if not pending:
            return
        texts = [r["text"] for r in pending]
        try:
            vectors = embed(texts, model=EMBED_MODEL, dimensions=EMBED_DIMS)
        except LLMError as exc:
            raise RuntimeError(f"embedding batch failed, aborting run: {exc}") from exc
        rows = []
        for rec, vec in zip(pending, vectors):
            payload = {
                "text": rec["text"],
                "source_agency": rec["agency"],
                "source_filename": rec["filename"],
                "citation": rec["citation"],
            }
            rows.append({
                "id": rec["id"],
                "sector": None,
                "content": json.dumps(payload, ensure_ascii=False),
                "embedding": to_vector_literal(vec),
            })
        upsert_batch(cur, rows)
        conn.commit()
        pending.clear()

    try:
        print("Processing sources:")
        for folder_name in SOURCE_FOLDERS:
            key = folder_name.lower()
            agency = AGENCY_LABEL[key]
            folder = existing_folders.get(key)

            if folder is None:
                print(f"  [{agency}] SKIPPED — no folder found (expected data/oracle_corpus/{folder_name}/)")
                continue

            pdfs = sorted(folder.glob("*.pdf"))
            if not pdfs:
                print(f"  [{agency}] 0 files — folder exists but contains no PDFs")
                continue

            for pdf_path in pdfs:
                relative_path = str(pdf_path.relative_to(DATA_DIR).as_posix())
                try:
                    text = extract_pdf_text(pdf_path)
                except Exception as exc:
                    files_skipped.append((relative_path, f"unreadable/corrupt PDF: {exc}"))
                    continue

                if len(text) < MIN_EXTRACT_CHARS:
                    files_skipped.append((relative_path, f"image-only or unextractable ({len(text)} chars extracted)"))
                    continue

                chunks = chunk_text(text, encoding)
                if not chunks:
                    files_skipped.append((relative_path, "no chunks produced after extraction"))
                    continue

                label = citation_label(agency, pdf_path.name)
                for idx, chunk in enumerate(chunks):
                    pending.append({
                        "id": chunk_id_for(relative_path, idx),
                        "text": chunk,
                        "agency": agency,
                        "filename": pdf_path.name,
                        "citation": label,
                    })
                    chunks_per_source[agency] += 1
                    if len(pending) >= BATCH_SIZE:
                        flush_pending()

                files_processed += 1

        flush_pending()

        cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
        total_rows = cur.fetchone()[0]
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print()
    print("Ingestion complete.")
    print(f"  Files processed: {files_processed}")
    print(f"  Files skipped:   {len(files_skipped)}")
    for path, reason in files_skipped:
        print(f"    - {path}: {reason}")
    print("  Chunks written per source:")
    for agency, count in chunks_per_source.items():
        print(f"    - {agency}: {count}")
    print(f"  Total rows now in {TABLE}: {total_rows}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console default (cp1252) can't print Arabic/·
    main()
