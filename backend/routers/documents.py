"""
Document upload — SME portal → Supabase Storage.

    POST /api/v1/applications/{application_id}/documents   (multipart/form-data: file)
      → 201 { document_id, filename, storage_url, status: "uploaded" }

Flow (architecture.md §4 — multipart-through-backend, the hackathon choice, not
signed-URL direct-to-storage):
  1. require SME role
  2. verify the application exists AND is owned by this SME (else 404 / 403)
  3. validate file (content-type allow-list + size cap)
  4. stream bytes to the private `application-documents` bucket
  5. insert an application_documents row
  6. return the document metadata + a short-lived signed URL

Storage is mediated by the backend (service-role); the bucket is private. The
persisted `storage_path` is the stable reference; `storage_url` in the response
is a freshly-signed, short-TTL URL so the review screen can preview immediately.

SCHEMA (confirmed against the live DB): applications.id (uuid PK),
applications.sme_profile_id (FK -> sme_profiles). Ownership resolves auth
user -> sme_profiles row -> applications.sme_profile_id.

application_documents predates this slice (from the "Design DB schema" task):
its PK is "id", not "document_id". The canonical columns are file_url,
file_type, is_zatca_verified, uploaded_at (CONVENTIONS.md) — this router
writes the object's storage path into file_url and its content type into
file_type. filename and status are the only columns this slice added; do not
reintroduce storage_path/content_type/created_at (see
migrations/001_application_documents_and_storage.sql).
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, UploadFile
from fastapi import File as FileParam

from core.auth import Principal, require_sme
from core.errors import APIError
from core.supabase import get_service_client
from schemas.documents import DocumentUploadResponse

# --- schema knobs -----------------------------------------------------------
APPLICATIONS_TABLE = "applications"
APPLICATIONS_ID_COL = "id"
APPLICATIONS_OWNER_COL = "sme_profile_id"  # FK -> sme_profiles PK
DOCUMENTS_TABLE = "application_documents"
DOCUMENTS_ID_COL = "id"  # pre-existing PK column, not "document_id"
BUCKET = "application-documents"

# Ownership resolves through sme_profiles, since applications.sme_profile_id is a
# profile FK, not the auth user id:
#   auth user (JWT)  ==  sme_profiles.<USER_COL>
#   sme_profiles.<ID_COL>  ==  applications.sme_profile_id
# ⚠️ Confirm these two column names against the real sme_profiles table.
SME_PROFILES_TABLE = "sme_profiles"
SME_PROFILES_ID_COL = "id"
SME_PROFILES_USER_COL = "user_id"

# --- upload policy ----------------------------------------------------------
MAX_BYTES = 15 * 1024 * 1024  # 15 MB — receipts/invoices/statements
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}
SIGNED_URL_TTL_SECONDS = 60 * 60  # 1 hour preview link

router = APIRouter(prefix="/api/v1", tags=["documents"])

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str | None) -> str:
    base = (name or "upload").rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    base = _SAFE_NAME.sub("_", base) or "upload"
    return base[:180]


def _caller_profile_id(svc, user_id: str) -> str:
    try:
        res = (
            svc.table(SME_PROFILES_TABLE)
            .select(SME_PROFILES_ID_COL)
            .eq(SME_PROFILES_USER_COL, user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        raise APIError(500, "db_error", "Could not resolve your SME profile.")
    rows = res.data or []
    if not rows:
        raise APIError(403, "no_sme_profile", "No SME profile is linked to this account.")
    return str(rows[0][SME_PROFILES_ID_COL])


def _assert_owned_application(svc, application_id: str, user_id: str) -> None:
    profile_id = _caller_profile_id(svc, user_id)
    try:
        res = (
            svc.table(APPLICATIONS_TABLE)
            .select(f"{APPLICATIONS_ID_COL},{APPLICATIONS_OWNER_COL}")
            .eq(APPLICATIONS_ID_COL, application_id)
            .limit(1)
            .execute()
        )
    except Exception:
        raise APIError(500, "db_error", "Could not look up the application.")

    rows = res.data or []
    if not rows:
        raise APIError(404, "application_not_found", "No application with that id.")
    if str(rows[0].get(APPLICATIONS_OWNER_COL)) != profile_id:
        # Don't leak existence details across owners.
        raise APIError(403, "forbidden", "You do not have access to this application.")


def _signed_url(svc, path: str) -> str:
    try:
        signed = svc.storage.from_(BUCKET).create_signed_url(path, SIGNED_URL_TTL_SECONDS)
    except Exception:
        return path  # fall back to raw path; GET /pdf can re-sign later
    if isinstance(signed, dict):
        return signed.get("signedURL") or signed.get("signedUrl") or path
    return getattr(signed, "signedURL", None) or getattr(signed, "signedUrl", None) or path


@router.post(
    "/applications/{application_id}/documents",
    status_code=201,
    response_model=DocumentUploadResponse,
)
async def upload_document(
    application_id: str,
    file: UploadFile = FileParam(...),
    principal: Principal = Depends(require_sme),
) -> DocumentUploadResponse:
    svc = get_service_client()

    # 1 + 2: role is enforced by require_sme; now enforce ownership.
    _assert_owned_application(svc, application_id, principal.user_id)

    # 3: validate.
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise APIError(
            415,
            "unsupported_media_type",
            "Upload a PDF or an image (PNG, JPEG, WebP, HEIC).",
        )

    data = await file.read()
    if not data:
        raise APIError(400, "empty_file", "The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise APIError(413, "file_too_large", "Files must be 15 MB or smaller.")

    # 4: stream to Storage.
    document_id = str(uuid.uuid4())
    filename = _safe_filename(file.filename)
    storage_path = f"{application_id}/{document_id}/{filename}"
    try:
        svc.storage.from_(BUCKET).upload(
            storage_path,
            data,
            {"content-type": content_type, "upsert": "false"},
        )
    except Exception:
        raise APIError(502, "storage_upload_failed", "Could not store the file. Try again.")

    # 5: record it.
    try:
        svc.table(DOCUMENTS_TABLE).insert(
            {
                DOCUMENTS_ID_COL: document_id,
                "application_id": application_id,
                "filename": filename,
                "status": "uploaded",
                # canonical columns (CONVENTIONS.md) — not storage_path/content_type
                "file_url": storage_path,
                "file_type": content_type,
            }
        ).execute()
    except Exception:
        # Best-effort cleanup so we don't orphan the object.
        try:
            svc.storage.from_(BUCKET).remove([storage_path])
        except Exception:
            pass
        raise APIError(500, "db_error", "Stored the file but could not record it. Try again.")

    # 6: respond.
    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        storage_url=_signed_url(svc, storage_path),
        status="uploaded",
    )
