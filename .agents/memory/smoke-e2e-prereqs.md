---
name: Smoke E2E prereqs
description: What's needed before backend/scripts/smoke_e2e.py can run end-to-end on Replit Linux.
---

## What was fixed
- Font paths: now cross-platform — resolves DejaVu on Linux, falls back to `ImageFont.load_default(size=N)` if no TTF found
- `_load_font(path, size)` helper wraps all `ImageFont.truetype()` calls in smoke_e2e.py
- `Pillow>=10.1` added to `backend/requirements.txt`

## What's still needed to run the full smoke
1. **`DATABASE_URL`** — Supabase IPv4 Session Pooler URL (not the direct IPv6-only host). Set as Replit Secret. Used by psycopg2 for direct DB ops in the script.
2. **Synthetic data seed** — run `python data/generate_synthetic_data.py --reset` with DATABASE_URL set; creates demo users (`mohammed@rawad-logistics.sa.demo`, `khalid@alinma.sa.demo`) and ground_truth.json documents.
3. **Port availability** — smoke_e2e.py starts its own uvicorn on port 8000; stop the Backend API workflow first or the script will get EADDRINUSE.
4. **Migration 004** — run `supabase/migrations/004_application_financing_fields.sql` in the Supabase SQL editor (adds amount/purpose/term_months/description columns).

## Partial smoke status (this session)
- Backend HTTP layer: ✅ 401 on unauthenticated calls (correct)
- Image render: ✅ DejaVu fonts resolve, 42KB JPEG output
- All 156 backend tests: ✅ pass
- TypeScript: ✅ zero errors
- Full E2E with OpenAI GPT calls: ⏳ blocked on items 1-4 above
