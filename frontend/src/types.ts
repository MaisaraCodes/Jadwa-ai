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
