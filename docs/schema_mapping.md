# Jadwa.ai Database & LangGraph State Mapping

This document outlines how our LangGraph agent state (`ApplicationState`) maps 1:1 onto our Supabase database.

Instead of building complex relational tables for every single AI output, we use **PostgreSQL JSONB columns** in the `agent_results` table. This allows our Python Pydantic models to dump data directly to the database, and the React frontend to fetch the entire dashboard state in a single API call.

## 1. Core Relational Tables

These tables handle the standard app functionality (Auth, file uploads, and basic tracking).

- **`sme_profiles`**: Stores Mohammed's (the SME) basic data (CR number, sector, district).
- **`applications`**: The master record for a loan application. Contains the `status` (`draft` → `processing` → `review_ready`).
- **`application_documents`**: Links Supabase Storage URLs (receipts, PDFs) to the application.

---

## 2. The agent_results Table (Agent Output Store)

This table uses the `application_id` as its primary key. Every time a LangGraph node finishes its job, it runs a simple `UPDATE` query on this table to save its output.

Here is the exact JSON structure (Pydantic schema) expected from each LangGraph node:

### Node 1: `document_intelligence_node`

- **Target Column:** `extracted_documents` (JSONB)
- **Goal:** Extract structured data and ZATCA QR codes from messy uploads.
- **Expected JSON Output:**

```json
[
  {
    "document_id": "uuid",
    "type": "zatca_receipt",
    "extracted_amount": 1500.50,
    "date": "2025-10-12",
    "zatca_verification_hash": "abc123xyz...",
    "confidence_score": 0.98
  }
]
```

### Node 2: `forensic_accountant_node`

- **Target Column:** `forensic_report` (JSONB)
- **Goal:** Cross-reference `extracted_documents` against the `mock_open_banking_ledger`.
- **Expected JSON Output:**

```json
{
  "overall_status": "yellow",
  "reconciliation_rate": 0.85,
  "discrepancy_flags": [
    {
      "severity": "high",
      "description": "ZATCA receipt amount (1500.50) does not match ledger debit (150.00) on 2025-10-12."
    }
  ]
}
```

### Node 3: `devils_advocate_node`

- **Target Column:** `weakness_report` (JSONB)
- **Goal:** Proactively find flaws in the SME's financial behavior.
- **Expected JSON Output:**

```json
{
  "critical_weaknesses": [
    "High reliance on a single vendor for 80% of inventory purchases."
  ],
  "mitigation_suggestions": [
    "Request evidence of secondary supplier contracts."
  ],
  "business_model_score": 72
}
```

### Node 4: `saudi_market_oracle_node`

- **Target Column:** `market_verdict` (JSONB)
- **Goal:** Use pgvector to retrieve SAMA/Monsha'at reports matching the SME's sector and district.
- **Expected JSON Output:**

```json
{
  "sector_trend": "growing",
  "district_saturation": "medium",
  "oracle_insight": "Logistics in Al-Kharj shows a 14% YoY growth, but fuel cost volatility remains a key risk factor according to recent SAMA briefings.",
  "sources_cited": [
    "SAMA SME Report Q3 2025"
  ]
}
```

### Node 5: `risk_sandbox_init_node`

- **Target Column:** `risk_baseline` (JSONB)
- **Goal:** Pre-calculate the math coefficients so the React UI sliders move at 60fps without LLM calls.
- **Expected JSON Output:**

```json
{
  "base_default_probability": 0.12,
  "revenue_volatility_multiplier": 1.05,
  "cash_buffer_months": 3.2,
  "recommended_interest_rate": 0.08
}
```

### Node 6: `aggregate_results_node`

- **Target Column:** `unified_application_record` (JSONB)
- **Goal:** Merge the outputs of the previous four parallel nodes into one clean payload for the `application_builder_node` to turn into a PDF, and for the React UI to consume.
- The record also carries `financing` (`ApplicationFinancing` — amount / purpose / term_months / description from the `applications` row, migration 004) so the final PDF states what is being applied for. On stored records that predate this field, the PDF builder falls back to reading the `applications` row directly.

### Node 7: `application_builder_node` → `applications.final_pdf_url`

- Renders `unified_application_record` to the Arabic PDF (WeasyPrint, no LLM), uploads it to Storage at `{application_id}/report.pdf`, and persists the bare object path in `applications.final_pdf_url` (signed on read by `GET /pdf`).
- The same builder is also invoked **on demand** by `GET /applications/{id}/pdf` and `GET /bank/applications/{id}/pdf` (`ensure_application_pdf`): cached when `final_pdf_url` points at a live Storage object, built now when it doesn't. If the aggregate column is empty, the builder assembles the record from the five individual `agent_results` columns.

---

## 3. External Data Simulations (For Hackathon Demo)

### `mock_open_banking_ledger`

Contains synthetic rows of bank transactions. The `forensic_accountant_node` will write SQL queries against this table to prove it can perform real reconciliation.

### `market_knowledge_base`

Contains vector embeddings of fake and/or real SAMA reports. The `saudi_market_oracle_node` will perform similarity searches here based on the SME's sector.
