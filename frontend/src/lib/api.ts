// Thin API layer for document upload.
// Uses XMLHttpRequest (not fetch) so we get real upload progress events for the
// SME's progress bar. Injects the Supabase JWT and normalizes the backend error
// envelope { error: { code, message } } into a typed ApiError.
import { supabase } from "./supabase";
import type { BankApplicationDetail, DocumentJSON, PatchDocumentRequest, UploadedDocument } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function bearerToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export function uploadDocument(
  applicationId: string,
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<UploadedDocument> {
  return new Promise(async (resolve, reject) => {
    const token = await bearerToken();
    if (!token) {
      reject(new ApiError(401, "unauthorized", "Your session expired. Sign in again."));
      return;
    }

    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/applications/${applicationId}/documents`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    // Do NOT set Content-Type — the browser sets the multipart boundary.

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };

    xhr.onerror = () =>
      reject(new ApiError(0, "network_error", "Network error while uploading. Check your connection."));

    xhr.onload = () => {
      let body: any = null;
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        /* non-JSON body */
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as UploadedDocument);
      } else {
        const code = body?.error?.code ?? "upload_failed";
        const message = body?.error?.message ?? "Upload failed. Try again.";
        reject(new ApiError(xhr.status, code, message));
      }
    };

    xhr.send(form);
  });
}

async function authedJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await bearerToken();
  if (!token) {
    throw new ApiError(401, "unauthorized", "Your session expired. Sign in again.");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  let body: any = null;
  try {
    body = await res.text().then((text) => (text ? JSON.parse(text) : null));
  } catch {
    /* non-JSON body */
  }

  if (!res.ok) {
    const code = body?.error?.code ?? "request_failed";
    const message = body?.error?.message ?? "Something went wrong. Try again.";
    throw new ApiError(res.status, code, message);
  }
  return body as T;
}

export function getExtractedDocuments(applicationId: string): Promise<{ documents: DocumentJSON[] }> {
  return authedJson(`/applications/${applicationId}/extracted`);
}

export function getBankApplication(applicationId: string): Promise<BankApplicationDetail> {
  return authedJson(`/bank/applications/${applicationId}`);
}

export function patchExtractedDocument(
  applicationId: string,
  documentId: string,
  patch: PatchDocumentRequest,
): Promise<DocumentJSON> {
  return authedJson(`/applications/${applicationId}/documents/${documentId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
