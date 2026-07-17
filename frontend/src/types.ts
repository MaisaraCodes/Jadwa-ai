// Mirrors backend/models.py shapes for the frontend (keep in the shared types.ts).
// Only the upload-related shapes are declared here; merge into your existing types.ts.

export interface UploadedDocument {
  document_id: string;
  filename: string;
  storage_url: string;
  status: "uploaded";
}

export type UploadStage = "queued" | "uploading" | "uploaded" | "failed";

export interface UploadItem {
  id: string; // client-side id for list keying (crypto.randomUUID)
  file: File;
  stage: UploadStage;
  progress: number; // 0..1
  error?: string;
  result?: UploadedDocument;
}

// Mirrors backend/models.py ForensicReport / DiscrepancyFlag (forensic_accountant_node
// output, schema_mapping.md Node 2). Do not redefine this shape elsewhere.
export type ForensicStatus = "green" | "yellow" | "red";
export type Severity = "high" | "medium" | "low";

export interface DiscrepancyFlag {
  severity: Severity;
  description: string;
}

export interface ForensicReport {
  overall_status: ForensicStatus;
  reconciliation_rate: number; // 0.0–1.0
  discrepancy_flags: DiscrepancyFlag[];
}

// Mirrors backend/models.py DocumentJSON (Node 1 — document_intelligence_node
// output, GET /applications/:id/extracted). SME review screen edits a copy of
// this, then PATCHes only the changed fields back.
export type DocumentType = "zatca_receipt" | "invoice" | "bank_statement" | "contract" | "other";

export interface DocumentJSON {
  document_id: string;
  type: DocumentType;
  vendor: string | null;
  extracted_amount: number;
  currency: string;
  date: string; // ISO yyyy-mm-dd
  line_items: string[];
  zatca_verification_hash: string | null;
  zatca_qr_base64: string | null;
  confidence_score: number; // 0.0-1.0
}

// Mirrors backend PatchDocumentRequest (routers/applications.py) — only the
// fields the SME can correct on the review screen.
export interface PatchDocumentRequest {
  extracted_amount?: number;
  date?: string;
  vendor?: string;
  type?: DocumentType;
}

// Mirrors backend/models.py SMEProfile / WeaknessReport / MarketVerdict /
// RiskBaseline and routers/bank.py's BankApplicationDetail response shape
// (GET /bank/applications/:id — architecture.md §4, "the ENTIRE dashboard
// in ONE call"). weakness_report / market_verdict / risk_baseline stay
// null until their Phase-2 nodes ship.
export type ApplicationStatus =
  | "draft"
  | "processing"
  | "review_ready"
  | "approved"
  | "rejected"
  | "more_info_needed";

// Mirrors backend routers/*.py GET /me (architecture.md §4 "Shared") — the
// only endpoint that returns anything about the signed-in user themselves.
// It has no business-specific fields (company_name, cr_number, sector,
// district) — full profile comes from GET /api/v1/me/profile (SMEProfile).
export interface Me {
  user_id: string;
  role: "sme" | "bank";
  display_name: string | null;
}

export interface SMEProfile {
  id: string;
  company_name: string;
  cr_number: string;
  sector: string;
  district: string;
  user_id: string | null;
  established_year?: number | null;
  backstory?: string | null;
}

// Mirrors backend routers/profile.py PatchProfileRequest — cr_number is
// intentionally absent (server enforces read-only; omit it from all PATCH calls).
export interface PatchProfileRequest {
  company_name?: string;
  sector?: string;
  district?: string;
  established_year?: number | null;
  backstory?: string | null;
}

export interface WeaknessReport {
  critical_weaknesses: string[];
  mitigation_suggestions: string[];
  business_model_score: number;
}

export interface MarketVerdict {
  sector_trend: "growing" | "stable" | "declining";
  district_saturation: "low" | "medium" | "high";
  oracle_insight: string;
  sources_cited: string[];
}

export interface RiskBaseline {
  base_default_probability: number;
  revenue_volatility_multiplier: number;
  cash_buffer_months: number;
  recommended_interest_rate: number;
}

// Mirrors backend routers/applications.py's ApplicationSummaryItem
// (GET /applications — the SME's own applications list).
export interface ApplicationSummaryItem {
  application_id: string;
  status: ApplicationStatus;
  created_at: string; // ISO datetime
  document_count: number;
  amount: number | null;
}

// Mirrors backend routers/applications.py DTOs for the application detail
// spine (create / process / status / submit / summary).
export interface CreateApplicationResponse {
  application_id: string;
  status: ApplicationStatus;
}

export interface ProcessResponse {
  status: ApplicationStatus;
}

export interface ApplicationStatusResponse {
  status: ApplicationStatus;
  nodes_completed: string[];
  progress: number; // 0.0-1.0
}

export interface SubmitResponse {
  status: ApplicationStatus;
}

export interface ApplicationSummaryResponse {
  health_summary: string;
  business_model_score: number | null;
  top_risks: string[];
}

// Mirrors backend routers/bank.py DecisionRequest/DecisionResponse
// (POST /bank/applications/:id/decision). "request_info" maps server-side
// to the real ApplicationStatus value "more_info_needed" — never "info_requested"
// (that's stale architecture.md prose; models.py's enum is canonical).
export type BankDecision = "approve" | "reject" | "request_info";

export interface DecisionResponse {
  status: ApplicationStatus;
}

// Mirrors backend routers/bank.py GET /bank/applications (architecture.md §4
// "the pre-scored queue").
export interface BankApplicationSummaryItem {
  application_id: string;
  sme_name: string;
  sector: string;
  district: string;
  submitted_at: string; // ISO datetime
  // null until the Phase-2 agents have scored the application (backend
  // routers/bank.py returns forensic_report.overall_status or None).
  forensic_status: ForensicStatus | null;
  business_model_score: number | null;
  amount: number | null;
}

export interface BankApplicationDetail {
  application_id: string;
  status: ApplicationStatus;
  sme_profile: SMEProfile;
  extracted_documents: DocumentJSON[];
  forensic_report: ForensicReport | null;
  weakness_report: WeaknessReport | null;
  market_verdict: MarketVerdict | null;
  risk_baseline: RiskBaseline | null;
  amount: number | null;
}
