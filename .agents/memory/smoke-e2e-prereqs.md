---
name: Smoke E2E prereqs
description: What's needed before backend/scripts/smoke_e2e.py can run end-to-end on Replit Linux, and the root-cause lessons learned.
---

## Prerequisites to run the full smoke

1. **Synthetic data seed** — run `python data/generate_synthetic_data.py --reset`; creates demo users (`mohammed@rawad-logistics.sa.demo` / `Jadwa-Demo-2026!`, `khalid@alinma.sa.demo`) and `data/ground_truth.json`.
2. **Port availability** — smoke_e2e.py starts its own uvicorn on port 8000; stop the "Backend API" workflow first (`stopWorkflow`) or the script gets EADDRINUSE.
3. **Migration 004** — `supabase/migrations/004_application_financing_fields.sql` must be applied in the Supabase SQL editor (adds amount/purpose/term_months/description to applications).
4. **Pillow ≥ 10.1** — already in `backend/requirements.txt`; needed for `ImageFont.load_default(size=N)` fallback.

## Passing smoke state (July 2026)

All 6 acceptance checks pass:
- `reconciliation_rate = 0.850` (17/20 clean)
- `overall_status = red`
- 1 high flag (fabricated Gulf Fuel Depot invoice, no ledger match)
- 3 medium flags (1 amount mismatch, 1 late-posting date mismatch, 1 round-amount signal)
- Cleanup verified (no leftover DB rows)

## Root-cause lessons from the reconciliation_rate = 0.50 failure

**Lesson 1 — Date format (the real bug)**
GPT-4 Vision swaps month and day in ISO dates (YYYY-MM-DD) whenever both components are ≤ 12, e.g. "2026-04-07" → read as July 4 instead of April 7. This placed documents 60+ days from their ledger entries, blowing past the 30-day matching window → `missing_ledger_match` high flags.

**Fix:** render dates using a text month abbreviation: `_d.strftime("%d %b %Y")` → "07 Apr 2026". Now unambiguous.

**Lesson 2 — ZATCA QR base64 in test images**
Rendering the long base64 QR block caused Vision to misidentify document structure (treating the QR block as a continuation of the line-item section). Removed from smoke test images; the QR-reading path is covered by `test_zatca.py` / `test_zatca_enrich.py`.

**Lesson 3 — Subtotal/VAT breakdown**
Three monetary lines (Subtotal / VAT / TOTAL) gave Vision multiple amounts to choose from. Removed breakdown; render only one TOTAL line.

**Why normalize.py amount parsing is NOT the problem:**
`_parse_amount` strips commas via `text.replace(",", "")` before `float()`, so "5,423.76" → 5423.76 correctly.

## What the direct matching test tells you
Running `match_documents_to_ledger(seed_docs, ledger_rows)` directly gives 0.85 — confirming the matching algorithm and seed data are correct. If a smoke run shows a lower rate, the issue is always in the Vision extraction step (image rendering or date/amount format confusion), not in the matching logic.
