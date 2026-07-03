# Jadwa.ai — Engineering Conventions

Read this at the start of **every** build chat. It exists so five separate chats produce code that fits together on the first merge. If something here conflicts with a doc, the docs (`architecture.md`, `schema_mapping.md`) win — fix this file in the same commit.

---

## Golden rules (the things that are easy to get wrong in isolation)

1. **Matching is Python, not LLM.** The forensic node reconciles invoices against the ledger in plain Python. The LLM is called only to write the human-readable `description` on each `DiscrepancyFlag`. Never ask a model to "check if these match."
2. **The Risk Sandbox is non-LLM and lives OUTSIDE the graph.** It's a pure function `recalculate(baseline, deltas) -> RiskProjection` behind a FastAPI endpoint. No model call ever happens on a slider move. Target < 150 ms.
3. **The forensic node reads the ledger in-node, from Postgres**, filtered by `sme_profile.cr_number`. The ledger is **not** passed through graph state. Bulk reference data stays out of state.
4. **ZATCA = offline TLV QR parse + structural validation.** There is no ZATCA API call. Decode the Base64 TLV (seller, VAT number, timestamp, total, VAT total, hash) and validate it locally. Say "parses/validates the ZATCA QR" everywhere — docs, UI, pitch.
5. **Each node writes ONLY its own state key.** `document_intelligence` → `extracted_documents`; the 4 agents → their own key each; `aggregate_results_node` → `unified_application_record`. No node overwrites another's key.
6. **`agent_results` is an output store, not a checkpointer.** Don't call it a LangGraph checkpointer anywhere.
7. **Import shapes from `models.py`.** Never hand-redefine `ForensicReport`, `DocumentJSON`, etc. in a node file.

---

## Repo layout

```
/frontend   React + TypeScript + Tailwind (Vite), deploys to Vercel
/backend    FastAPI, LangGraph orchestrator, the 6 nodes, risk_calc_engine, PDF builder
/data       generate_synthetic_data.py + any local fixtures
/docs       architecture.md, schema_mapping.md, this file, models.py lives in /backend
```

Put `models.py` in `/backend` and import it from every node. The frontend mirrors these shapes as TypeScript types (keep them in one `types.ts`).

---

## The node contract (architecture.md §1)

| Node | Reads | Writes | Model |
|---|---|---|---|
| `document_intelligence_node` | raw files | `extracted_documents` | **GPT-5.4** (vision) |
| `forensic_accountant_node` | `extracted_documents`, `sme_profile.cr_number` (+ ledger from Postgres) | `forensic_report` | **GPT-5.4 Mini** |
| `devils_advocate_node` | `extracted_documents`, `sme_profile` | `weakness_report` | **GPT-5.4** |
| `saudi_market_oracle_node` | `sme_profile.sector`, `sme_profile.district` | `market_verdict` | **GPT-5.4 Mini** + `text-embedding-3-large` |
| `risk_sandbox_init_node` | `extracted_documents` | `risk_baseline` | none (Python) |
| `aggregate_results_node` | all 4 outputs | `unified_application_record` | none |
| `application_builder_node` | `unified_application_record` | PDF + status | WeasyPrint, no LLM |

The four middle nodes are **independent** — fan them out in parallel (`dispatch` → 4 → `aggregate`). LangGraph joins automatically once all four edges arrive.

---

## Models & embeddings (locked)

- Confirm the exact ID strings (`gpt-5.4`, `gpt-5.4-mini`) in the OpenAI dashboard before hardcoding.
- Embeddings: `text-embedding-3-large`, truncate to **1024–1536 dims** via the `dimensions` param to keep the pgvector index fast.
- Put every model call behind one thin wrapper (`llm.py`) so a model swap is one line, and Arabic prompts are handled consistently (prompt in English where it doesn't hurt quality — Arabic is token-heavy).

---

## API (architecture.md §4)

- Base path `/api/v1`. Auth: `Authorization: Bearer <supabase_jwt>`; FastAPI derives `user_id` + `role`. No custom login endpoints (Supabase Auth is client-side).
- `sme` routes require role `sme` **and** ownership; `bank` routes require role `bank`. Cross-role → `403`.
- Errors: `{ "error": { "code": string, "message": string } }` + proper HTTP status.
- JSON everywhere except document upload (`multipart/form-data`).
- Status polling for the live-parse animation (`GET /status` every 1–2 s). No SSE for the hackathon.

---

## application_documents canonical columns

`file_url`, `file_type`, `is_zatca_verified`, `uploaded_at` (plus `filename` and `status` added for the upload slice) are canonical — `storage_path`, `content_type`, and `created_at` were dropped as redundant and must not be reintroduced.

---

## Frontend

- **Shared brand core:** night (`--bg` dark) / ivory (`--bg` light) / **gold**. Gold is restricted to the mark's diamond, verification/brand moments, and the Sadu band — never a generic CTA inside a portal.
- **Two portal accents (replaces teal/coral):** `data-portal="sme"` → **oasis teal**; `data-portal="bank"` → **falcon blue**. Never blend them; the portal is unmistakable from its accent + canvas tint.
- **`green/amber/red` are reserved for forensic/system status only** (`pass/review/flag`), mapped 1:1 to `ForensicStatus`. The brand palette never uses them.
- **Dark + light are one system:** semantic tokens in `tokens.css`, `darkMode: 'class'`, accent via `data-portal`. Author each component **once**.
- **RTL is default-capable:** logical Tailwind utilities only (`ms/me/ps/pe/start/end/border-s/text-start`); `dir`+`lang` on `<html>`; Western digits + `tabular-nums` for all figures.
- Type: **Zain** (display) + **Alexandria** (body), both Arabic-native, via Google Fonts.
- The bank dashboard still fetches the whole application in one call and reads the `unified_application_record` shape; the sandbox still sends only `deltas` and renders `RiskProjection`.

See `docs/DESIGN_SYSTEM.md` for the full visual system (tokens, type scale, components) — it is the single source of visual truth and supersedes the old teal/coral rule.

---

## Git

- Branch per surface: `feat/forensic-node`, `feat/sme-portal`, etc. Small PRs. `main` stays deployable (Vercel auto-deploys it).
- Never commit `.env`. Keep `.env.example` current.

---

## Chat kickoff line (paste at the top of every build chat)

> `[Maisara/Osama] here — building <node/phase>. Read architecture.md §<n>, schema_mapping.md, models.py, and follow CONVENTIONS.md.`
