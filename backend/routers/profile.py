"""
SME profile self-service — role: sme, ownership enforced.

    GET  /api/v1/me/profile   -> SMEProfile (caller's own profile)
    PATCH /api/v1/me/profile  -> SMEProfile (update editable fields)

cr_number is READ-ONLY — it keys the forensic ledger lookup (CONVENTIONS.md §1)
and must never be mutated via the API. All other profile fields are editable.

Ownership: caller's Supabase JWT user_id must match sme_profiles.user_id.
403 if no sme_profiles row exists for this user (they haven't been set up yet).
Standard error shape: { "error": { "code": string, "message": string } }.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.auth import Principal, require_sme
from core.errors import APIError
from core.supabase import get_service_client
from models import SMEProfile

SME_PROFILES_TABLE = "sme_profiles"
SME_PROFILES_ID_COL = "id"
SME_PROFILES_USER_COL = "user_id"

router = APIRouter(prefix="/api/v1/me", tags=["profile"])


# ---------------------------------------------------------------------------
# Request / response DTOs
# ---------------------------------------------------------------------------

class PatchProfileRequest(BaseModel):
    """Fields the SME is allowed to update. cr_number is intentionally absent."""
    company_name: str | None = None
    sector: str | None = None
    district: str | None = None
    established_year: int | None = None
    backstory: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_own_profile(svc, user_id: str) -> dict:
    """Return the sme_profiles row for this user, or raise 403."""
    try:
        res = (
            svc.table(SME_PROFILES_TABLE)
            .select("*")
            .eq(SME_PROFILES_USER_COL, user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        raise APIError(500, "db_error", "Could not fetch your SME profile.")
    rows = res.data or []
    if not rows:
        raise APIError(
            403,
            "no_sme_profile",
            "No SME profile is linked to this account. Contact your administrator.",
        )
    return rows[0]


def _row_to_profile(row: dict) -> SMEProfile:
    return SMEProfile(
        id=str(row[SME_PROFILES_ID_COL]),
        company_name=row.get("company_name", ""),
        cr_number=row.get("cr_number", ""),
        sector=row.get("sector", ""),
        district=row.get("district", ""),
        user_id=row.get("user_id"),
        established_year=row.get("established_year"),
        backstory=row.get("backstory"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=SMEProfile)
async def get_profile(principal: Principal = Depends(require_sme)) -> SMEProfile:
    """Return the authenticated SME's own profile."""
    svc = get_service_client()
    row = _get_own_profile(svc, principal.user_id)
    return _row_to_profile(row)


@router.patch("/profile", response_model=SMEProfile)
async def patch_profile(
    body: PatchProfileRequest,
    principal: Principal = Depends(require_sme),
) -> SMEProfile:
    """Update editable profile fields. cr_number is always read-only."""
    svc = get_service_client()
    row = _get_own_profile(svc, principal.user_id)
    profile_id = str(row[SME_PROFILES_ID_COL])

    # Build update payload — only send fields the caller actually supplied.
    updates: dict = {}
    if body.company_name is not None:
        updates["company_name"] = body.company_name
    if body.sector is not None:
        updates["sector"] = body.sector
    if body.district is not None:
        updates["district"] = body.district
    if body.established_year is not None:
        updates["established_year"] = body.established_year
    if body.backstory is not None:
        updates["backstory"] = body.backstory

    if not updates:
        # Nothing to do — return the current profile as-is.
        return _row_to_profile(row)

    try:
        res = (
            svc.table(SME_PROFILES_TABLE)
            .update(updates)
            .eq(SME_PROFILES_ID_COL, profile_id)
            .execute()
        )
    except Exception:
        raise APIError(500, "db_error", "Could not update your profile.")

    updated_rows = res.data or []
    if not updated_rows:
        raise APIError(500, "db_error", "Profile update did not return the updated row.")
    return _row_to_profile(updated_rows[0])
