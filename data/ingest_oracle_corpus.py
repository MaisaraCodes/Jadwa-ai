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

Run:
  python data/ingest_oracle_corpus.py              (idempotent — upsert by uuid5 id)
  python data/ingest_oracle_corpus.py --reset      (delete-per-file then re-insert)
  python data/ingest_oracle_corpus.py --ocr        (route image-only files via pytesseract)

Env: OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, DATABASE_URL
     DATABASE_URL must be the Supabase IPv4 Session Pooler URL (pooler.supabase.com:5432),
     NOT the direct db.<ref>.supabase.co URL (IPv6-only; unreachable from Replit).
Deps: psycopg2-binary, pymupdf, tiktoken, python-dotenv (backend/requirements.txt)

--------------------------------------------------------------------------------
LIVE SCHEMA — migration 003 applied.

    market_knowledge_base
      id              uuid        PK
      sector          text        nullable  (left NULL — general regulator reports)
      content         text        NOT NULL  (clean prose chunk — NOT JSON)
      embedding       vector(1536) nullable
      source_agency   text
      source_filename text
      citation        text
      chunk_index     int

Retrieval note: similarity search is purely on `embedding` (no sector filter).
`sector` is reserved for sme_profile.sector values (logistics/cafe/retail/…);
writing an agency name into it would silently break that future filter.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import os
import sys
import unicodedata
import uuid
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

# Allow `from core.llm import embed` — backend/ is not a package on sys.path by default.
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / "backend" / ".env")
load_dotenv()  # project-root .env as fallback

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TABLE = "market_knowledge_base"
CORPUS_ROOT = Path(__file__).parent / "oracle_corpus"
CHUNK_SIZE = 400          # tokens per chunk (tiktoken cl100k_base)
OVERLAP = 50              # token overlap between adjacent chunks
BATCH_SIZE = 20           # chunks per OpenAI embeddings call
MIN_EXTRACT_CHARS = 200   # fewer chars → quarantine as "image-only"
PRES_FORM_THRESHOLD = 0.15  # >15% of Arabic-ish codepoints are pres-forms → garbled

# Stable namespace for deterministic uuid5 chunk IDs (post-migration-003).
# Using a new namespace vs. the pre-003 draft intentionally — old JSON-in-content
# rows won't collide; run with --reset on the first ingest to purge them.
_UUID_NS = uuid.UUID("3a1b4c2d-5e6f-7890-abcd-ef1234567890")


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

class ExtractionStats(NamedTuple):
    char_count: int
    arabic_pct: float     # arabic_block_codepoints / total_non_whitespace
    presform_pct: float   # pres_form_codepoints / (arabic_block + pres_forms)


def _is_arabic_block(cp: int) -> bool:
    return 0x0600 <= cp <= 0x06FF


def _is_pres_form(cp: int) -> bool:
    """True for Arabic presentation-form codepoints (FB50–FDFF and FE70–FEFF)."""
    return (0xFB50 <= cp <= 0xFDFF) or (0xFE70 <= cp <= 0xFEFF)


def extraction_stats(text: str) -> ExtractionStats:
    """Compute extraction quality metrics. Input must already be NFKC-normalised."""
    non_ws = sum(1 for c in text if not c.isspace())
    arabic_block = sum(1 for c in text if _is_arabic_block(ord(c)))
    pres_forms = sum(1 for c in text if _is_pres_form(ord(c)))
    arabic_ish = arabic_block + pres_forms

    arabic_pct = arabic_block / non_ws if non_ws else 0.0
    presform_pct = pres_forms / arabic_ish if arabic_ish else 0.0
    return ExtractionStats(
        char_count=len(text),
        arabic_pct=arabic_pct,
        presform_pct=presform_pct,
    )


def quality_gate(text: str, stats: ExtractionStats) -> str | None:
    """Return a quarantine reason string, or None if the file passes the gate."""
    if stats.char_count < MIN_EXTRACT_CHARS:
        return f"image-only: {stats.char_count} chars"
    if stats.presform_pct > PRES_FORM_THRESHOLD:
        return f"likely garbled: {stats.presform_pct:.1%} pres-forms"
    return None


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(path: Path) -> str:
    """Extract text from all pages and NFKC-normalise (removes presentation-form bias)."""
    try:
        import fitz  # pymupdf
    except ImportError as exc:
        raise RuntimeError("pymupdf is not installed") from exc

    doc = fitz.open(str(path))
    pages = [page.get_text() for page in doc]
    doc.close()
    raw = "\n".join(pages)
    return unicodedata.normalize("NFKC", raw)


def ocr_extract(path: Path) -> str | None:
    """OCR fallback via pytesseract (ara+eng). Returns None if unavailable."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        return None  # caller logs the skip message

    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pages.append(pytesseract.image_to_string(img, lang="ara+eng"))
    doc.close()
    raw = "\n".join(pages)
    return unicodedata.normalize("NFKC", raw)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, encoding) -> list[str]:
    """Split text into CHUNK_SIZE-token chunks with OVERLAP-token stride."""
    tokens = encoding.encode(text)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk = encoding.decode(tokens[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(tokens):
            break
        start = end - OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunk_id_for(relative_path: str, chunk_index: int) -> str:
    """Deterministic uuid5 so re-runs upsert cleanly without duplicates."""
    return str(uuid.uuid5(_UUID_NS, f"{relative_path}:{chunk_index}"))


def citation_label(agency: str, filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").title()
    return f"{agency} — {stem}"


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def _flush_batch(cur, pending: list[dict], embeddings: list[list[float]]) -> None:
    """INSERT/UPSERT one batch of chunks into market_knowledge_base."""
    from psycopg2.extras import execute_values

    rows = [
        (
            item["id"],
            None,               # sector — NULL for general regulator reports
            item["text"],       # content: clean prose
            item["agency"],     # source_agency
            item["filename"],   # source_filename
            item["citation"],   # citation
            item["chunk_index"],
            emb,                # embedding
        )
        for item, emb in zip(pending, embeddings)
    ]

    execute_values(
        cur,
        f"""
        INSERT INTO {TABLE}
            (id, sector, content, source_agency, source_filename,
             citation, chunk_index, embedding)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            content         = EXCLUDED.content,
            source_agency   = EXCLUDED.source_agency,
            source_filename = EXCLUDED.source_filename,
            citation        = EXCLUDED.citation,
            chunk_index     = EXCLUDED.chunk_index,
            embedding       = EXCLUDED.embedding
        """,
        rows,
        template="(%s, %s, %s, %s, %s, %s, %s, %s::vector)",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest oracle PDF corpus into market_knowledge_base."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="DELETE existing rows per file (by source_filename) before re-inserting. "
             "Use when CHUNK_SIZE/OVERLAP changed to avoid orphaned stale chunks.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Route image-only quarantined files through pytesseract (ara+eng) if available.",
    )
    args = parser.parse_args()

    # Validate hard dependencies
    try:
        import tiktoken
    except ImportError as exc:
        sys.exit(f"tiktoken not installed: {exc}")
    try:
        import psycopg2  # noqa: F401
    except ImportError as exc:
        sys.exit(f"psycopg2-binary not installed: {exc}")

    from core.llm import LLMError, embed

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit(
            "DATABASE_URL is not set.\n"
            "Export the Supabase IPv4 Session Pooler URL:\n"
            "  postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres"
        )

    encoding = tiktoken.get_encoding("cl100k_base")
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    files_processed = 0
    files_skipped: list[tuple[str, str]] = []
    chunks_per_source: dict[str, int] = defaultdict(int)
    pending: list[dict] = []

    def flush_pending() -> None:
        if not pending:
            return
        try:
            embeddings = embed([item["text"] for item in pending])
        except LLMError as exc:
            print(f"  [WARN] Embedding batch failed: {exc} — skipping {len(pending)} chunks")
            pending.clear()
            return
        try:
            _flush_batch(cur, pending, embeddings)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        pending.clear()

    def queue_chunks(text: str, agency: str, pdf_path: Path, relative_path: str) -> int:
        """Chunk text and add to pending; returns number of chunks queued."""
        chunks = chunk_text(text, encoding)
        if not chunks:
            return 0
        label = citation_label(agency, pdf_path.name)
        for idx, chunk in enumerate(chunks):
            pending.append({
                "id": chunk_id_for(relative_path, idx),
                "text": chunk,
                "agency": agency,
                "filename": pdf_path.name,
                "citation": label,
                "chunk_index": idx,
            })
            chunks_per_source[agency] += 1
            if len(pending) >= BATCH_SIZE:
                flush_pending()
        return len(chunks)

    try:
        for agency_dir in sorted(CORPUS_ROOT.iterdir()):
            if not agency_dir.is_dir():
                continue
            agency = agency_dir.name

            for pdf_path in sorted(agency_dir.glob("*.pdf")):
                relative_path = f"{agency}/{pdf_path.name}"

                # ── Extract ──────────────────────────────────────────────
                try:
                    text = extract_pdf_text(pdf_path)
                except Exception as exc:
                    print(f"  {relative_path}: extraction error → SKIP: {exc}")
                    files_skipped.append((relative_path, f"extraction error: {exc}"))
                    continue

                stats = extraction_stats(text)
                reason = quality_gate(text, stats)

                # Per-file diagnostic
                print(
                    f"  {relative_path}: "
                    f"{stats.char_count} chars, "
                    f"arabic={stats.arabic_pct:.1%}, "
                    f"presform={stats.presform_pct:.1%}"
                    + (f" → QUARANTINE: {reason}" if reason else " → OK")
                )

                # ── Quality gate ─────────────────────────────────────────
                if reason:
                    ocr_attempted = False
                    if args.ocr and "image-only" in reason:
                        ocr_attempted = True
                        try:
                            import pytesseract  # noqa: F401
                            ocr_text = ocr_extract(pdf_path)
                        except ImportError:
                            print(
                                f"    OCR requested but pytesseract unavailable — "
                                f"skipping {pdf_path.name}"
                            )
                            ocr_text = None

                        if ocr_text is not None:
                            ocr_stats = extraction_stats(ocr_text)
                            ocr_reason = quality_gate(ocr_text, ocr_stats)
                            if ocr_reason:
                                print(f"    OCR result also quarantined: {ocr_reason}")
                                files_skipped.append((relative_path, f"{reason} (OCR also: {ocr_reason})"))
                                continue
                            # OCR succeeded — use that text
                            text = ocr_text
                            print(f"    OCR succeeded for {pdf_path.name}")
                        else:
                            files_skipped.append((relative_path, reason))
                            continue
                    else:
                        files_skipped.append((relative_path, reason))
                        continue

                # ── Reset (optional) ─────────────────────────────────────
                if args.reset:
                    cur.execute(
                        f"DELETE FROM {TABLE} WHERE source_filename = %s",
                        (pdf_path.name,),
                    )
                    conn.commit()

                # ── Chunk & queue ────────────────────────────────────────
                n = queue_chunks(text, agency, pdf_path, relative_path)
                if n == 0:
                    files_skipped.append((relative_path, "no chunks produced after extraction"))
                    continue

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

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    print("Ingestion complete.")
    print(f"  Files processed : {files_processed}")
    print(f"  Files skipped   : {len(files_skipped)}")
    for path, skip_reason in files_skipped:
        print(f"    - {path}: {skip_reason}")
    print("  Chunks written per source:")
    for source_agency, count in sorted(chunks_per_source.items()):
        print(f"    - {source_agency}: {count}")
    print(f"  Total rows now in {TABLE}: {total_rows}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
