# Jadwa.ai — API Contract (FINALIZED)

Supersedes the endpoint list in `architecture.md §4` where they conflict. Reconciled
against the LIVE database (the DB is the source of truth). Frontend and the Phase-2
LangGraph nodes build against **this** file.

## Conventions (unchanged)
- Base path `/api/v1`. Auth: `Authorization: Bearer <supabase_jwt>` on everything except `/health`.
- `sme` routes require role `sme` **and** ownership of the application; `bank` routes require role `bank`. Cross-role → `403`.
- Errors: `{ "error": { "code": string, "message": string } }` + proper HTTP status.
- JSON everywhere except document upload (`multipart/form-data`).

## Status lifecycle — REAL enum (no `submitted`)
```
draft ──▶ processing ──▶ review_ready ──▶ approved | rejected | more_info_needed
```
- Valid `applications.status` values: `draft, processing, review_ready, approved, rejected, more_info_needed`.
- **`review_ready` is the bank-queue status** (what the synthetic data seeds). The doc's `submitted`
  is collapsed into `review_ready`; the doc's `info_requested` is `more_info_needed`.

## Field mappings (doc → real)
- `sme_name` → `sme_profiles.company_name`
- `submitted_at` → `applications.updated_at` (no dedicated column)
- `models.py::SMEProfile`: rename `name`→`company_name`, `sme_id`→`id`, make `established_year`/`backstory`
  optional; add `user_id: str | None`. Fix in this task (nodes import it next).

## "Real" vs "stub"
- **REAL** = returns live data (works today, backed by the seeded dataset).
- **STUB** = correct route/guard/shape, placeholder body until its node exists. Node-output fields
  (`forensic_report`, `weakness_report`, `market_verdict`, `risk_baseline`, `business_model_score`,
  `forensic_status`) are `null`/`"pending"` until Phase 2 writes them to `agent_results`.

---

## Shared
| Method | Path | Guard | Response | Status |
|---|---|---|---|---|
| GET | `/me` | any auth | `{ user_id, role, display_name }` | REAL — from JWT + `user_metadata.display_name` (fallback email) |

## SME portal (role `sme` + ownership)
| Method | Path | Req body | Response | Status |
|---|---|---|---|---|
| POST | `/applications` | `{ requested_amount? }` | `201 { application_id, status:"draft" }` | REAL — insert draft for caller's profile. `requested_amount` is NOT NULL in DB → default `0` if omitted. |
| GET | `/applications` | — | `200 { applications:[{ application_id, status, created_at, document_count }] }` | REAL — caller's apps; `document_count` from `application_documents`. |
| POST | `/applications/{id}/documents` | multipart `file` | `201 { document_id, filename, storage_url, status:"uploaded" }` | **DONE** (existing `documents.py`). |
| POST | `/applications/{id}/process` | — | `202 { status:"processing" }` | STUB — set status `processing`; no graph run yet. |
| GET | `/applications/{id}/status` | — | `200 { status, nodes_completed:[...], progress }` | STUB — real `status`; `nodes_completed`/`progress` derived (review_ready → all 6 done, progress 1.0). |
| GET | `/applications/{id}/extracted` | — | `200 { documents:[DocumentJSON,...] }` | REAL — `agent_results.extracted_documents` (seeded). |
| PATCH | `/applications/{id}/documents/{document_id}` | `{ extracted_amount?, date?, vendor?, type? }` | `200 { document_id, ...updated }` | REAL — patch the matching element inside `extracted_documents` JSONB, write back. |
| POST | `/applications/{id}/submit` | — | `200 { status:"review_ready" }` | REAL — set `review_ready` (enters bank queue); best-effort idempotent PDF build (failure deferred to GET /pdf). |
| GET | `/applications/{id}/summary` | — | `200 { health_summary, business_model_score, top_risks:[...] }` | STUB — from `weakness_report` if present, else placeholder text + `null` score. |
| GET | `/applications/{id}/pdf` | — | `200 { pdf_url }` | REAL — self-healing: serve the cached report if `final_pdf_url` points at a live Storage object, else build now (`ensure_application_pdf`), persist, and sign. `null` only while no agent output exists; build failure → `500 pdf_build_failed`. Bank mirror: `GET /bank/applications/{id}/pdf`. |

## Bank dashboard (role `bank`)
| Method | Path | Req | Response | Status |
|---|---|---|---|---|
| GET | `/bank/applications` | `?status=review_ready&sort=updated_at&order=desc` | `200 { applications:[{ application_id, sme_name, sector, district, submitted_at, forensic_status, business_model_score }] }` | REAL — apps by status (default `review_ready`) joined to `sme_profiles`; `sme_name`=`company_name`, `submitted_at`=`updated_at`; `forensic_status`/`business_model_score` from `agent_results` (**null until Phase 2**). |
| GET | `/bank/applications/{id}` | — | `200 { application_id, status, sme_profile, extracted_documents, forensic_report, weakness_report, market_verdict, risk_baseline }` | REAL — whole record from `applications`+`sme_profiles`+`agent_results` in ONE call. Node outputs `null` until Phase 2. |
| POST | `/bank/applications/{id}/sandbox/recalculate` | `{ deltas:{ revenue_growth, cost_increase, customer_churn, demand_shift, interest_rate, oil_price_sensitivity } }` | `200 { projection:{ months:[12], cash_flow:[12], risk_score, risk_class, summary_line } }` | STUB — deterministic placeholder projection from `deltas` + a default baseline (real `risk_baseline` not seeded). Pure Python, no LLM. Replace math with the Phase-4 `risk_calc_engine`. |
| POST | `/bank/applications/{id}/decision` | `{ decision:"approve"\|"reject"\|"request_info", note? }` | `200 { status }` | REAL — map `approve→approved`, `reject→rejected`, `request_info→more_info_needed`; set status. |

---

## Notes for implementers
- All rich shapes (`DocumentJSON`, `ForensicReport`, `ApplicationRecord`, `RiskProjection`, etc.)
  import from `models.py` — never hand-redefine (CONVENTIONS rule #7).
- Ownership check for `sme` routes reuses the pattern in `routers/documents.py`
  (auth user → `sme_profiles` row → `applications.sme_profile_id`).
- The bank dashboard reads the whole application in ONE call (`GET /bank/applications/{id}`) —
  keep it a single round-trip.
- Sandbox: client sends ONLY `deltas`; the baseline never leaves the server.
