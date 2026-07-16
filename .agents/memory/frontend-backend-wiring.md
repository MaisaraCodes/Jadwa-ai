---
name: Frontend-backend wiring conventions
description: How PENDING BACKEND stubs were eliminated; patterns for future endpoints.
---

## Rule
When a new backend endpoint ships, ALL of these must change in the same PR:
1. `frontend/src/types.ts` — update the mirrored interface to add new fields (always optional with `null` default so old data doesn't break)
2. `frontend/src/lib/api.ts` — add the API function; update existing ones that now have new params
3. The consuming component — replace local state with real API call; keep loading/error/empty states
4. `frontend/src/i18n/strings.ts` — add any new string keys (both ar + en)
5. Remove every `// PENDING BACKEND` comment that is resolved

## Key decisions made
- `BankApplicationSummaryItem.amount` and `ApplicationSummaryItem.amount` are `number | null` (not `undefined`) — matches Pydantic `Optional[float] = None`
- `SMEProfile` now includes `established_year?: number | null` and `backstory?: string | null`; `PatchProfileRequest` omits `cr_number` (enforced read-only server-side)
- `listBankApplications()` filters `?status=review_ready` (not `submitted` — that status was removed from the enum)
- `createApplication()` now accepts `{ amount, purpose, term_months, description }` and sends them all to the POST body
- Market verdict badges use `accent-soft/accent-strong` tokens ONLY — never `pass/review/flag` which are reserved exclusively for ForensicStatus (DESIGN_SYSTEM.md §4.1)

**Why:** pass/review/flag tokens carry forensic traffic-light meaning; mixing them into market verdict would confuse bank officers reading the detail page.
