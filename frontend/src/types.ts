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
