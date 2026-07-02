# `generate_synthetic_data.py` — Spec

This script is the **critical-path blocker** for Phase 2 and Phase 3: the forensic node has nothing to reconcile against, and the demo has nothing to show, until this dataset exists. Build it first.

**Goal:** one Python script that populates Supabase Postgres directly with a convincing, reproducible dataset — Saudi SME profiles, their "ground-truth" open-banking ledger, and a set of invoices/receipts that includes deliberate fakes for the Forensic Accountant to catch.

**Out of scope:** the Saudi Market Oracle corpus (SAMA/Monsha'at/GASTAT) and its embeddings — that's a separate Phase 3 task. This script does **not** touch `market_knowledge_base`.

---

## Outputs (write directly to Postgres)

1. **`sme_profiles`** — 5–8 rows. Fields match `SMEProfile` in `models.py`: `sme_id`, `name`, `cr_number` (unique — this keys everything), `sector`, `district`, `established_year`, `backstory`.
   - Vary sectors: logistics, café/F&B, construction supplier, retail shop, small manufacturer, etc.
   - Use real Saudi districts (e.g. Al-Kharj, and Riyadh districts) so the Oracle has something plausible to match later.

2. **`mock_open_banking_ledger`** — 12–18 months of transactions per SME. This is the ground truth.
   - Suggested columns: `txn_id`, `cr_number` (FK to the SME), `date`, `amount` (signed: credit +, debit −), `counterparty`, `description`, `running_balance`.
   - Make it realistic: recurring revenue inflows, recurring costs (rent, payroll, and sector-specific — fuel for logistics, ingredients for a café), plus seasonality. This realism is what makes the forensic match believable.

3. **Invoices / receipts** — a set per SME, stored wherever `application_documents` / extracted docs live, shaped like `DocumentJSON`: `document_id`, `type` (`zatca_receipt` | `invoice`), `vendor`, `extracted_amount`, `currency` (`SAR`), `date`, `zatca_verification_hash`, `confidence_score`.

---

## The invoice mix (this is the whole point)

Per SME, generate three buckets so the forensic node has clear signal:

- **Legitimate & reconciling** (majority): each has a matching ledger debit within tolerance (amount ±, date window). → should clear **green**.
- **Fabricated** (1–2 per SME): no matching ledger transaction at all. → forensic flags **red**.
- **Genuine mismatch / noise** (1–2 per SME): a real timing gap or small amount difference — realistic bookkeeping noise, not fraud. → **yellow**.

Make sure the set collectively exercises all **three fraud signals** the forensic node implements:
1. no matching transaction found,
2. amount mismatch beyond tolerance,
3. suspiciously round or repeated identical amounts.

---

## Synthetic ZATCA QR (so the ZATCA-parse task has real input)

For each `zatca_receipt`, generate a **Base64, TLV-encoded** QR payload with the standard Phase-2 tags so the offline parser has authentic-looking data to decode and validate:

| Tag | Field |
|---|---|
| 1 | Seller name |
| 2 | VAT registration number |
| 3 | Timestamp (ISO-8601) |
| 4 | Invoice total (with VAT) |
| 5 | VAT total |

(Confirm the exact tag order against ZATCA's current published spec when implementing.) For fabricated invoices, you can still emit a well-formed QR — the forensic catch comes from the **ledger mismatch**, not from a malformed QR. `zatca_verification_hash` can be a synthetic hash string.

---

## Reproducibility & demo support

- **Fixed random seed** at the top of the script so every run produces the identical dataset — demos must be repeatable.
- Emit a **`ground_truth.json` manifest** listing which `document_id`s are fabricated / mismatched, with the reason. This is for automated tests and for the demo narration ("the system flagged invoice X because…") — never expose it to the model.
- Put volume knobs at the top: `N_SMES`, `MONTHS_OF_HISTORY`, `FABRICATED_PER_SME`, `MISMATCH_PER_SME`, tolerances.

---

## Acceptance criteria (mirrors the Phase 2 board exit)

Upload a batch for one test SME that includes at least one fabricated invoice, and:

- the fabricated invoice is flagged **red** with a clear, specific reason,
- the genuine-mismatch invoice is flagged **yellow**,
- every legitimate invoice clears **green**,
- `reconciliation_rate` and `overall_status` on the `ForensicReport` reflect the mix.

If that run passes, the dataset is doing its job and Phase 2 is unblocked.
