"""
Auth dependency (CONVENTIONS.md / architecture.md §4).

Validates the `Authorization: Bearer <supabase_jwt>` header, resolves it to a
Supabase user, and derives (user_id, role). Role is read from the JWT's
app_metadata.role (fallback user_metadata.role), values: "sme" | "bank".

NOTE — this is the interim implementation that unblocks the upload endpoint.
Task #3 ("Build basic auth flow with two roles") will own the canonical version;
when it lands, keep this SAME public surface (get_current_user -> Principal,
require_sme, require_bank) so downstream routers don't change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Header

from .errors import APIError
from .supabase import get_anon_client

Role = Literal["sme", "bank"]


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise APIError(401, "unauthorized", "Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise APIError(401, "unauthorized", "Empty bearer token.")
    return token


async def get_current_user(authorization: str | None = Header(default=None)) -> Principal:
    token = _extract_bearer(authorization)
    try:
        resp = get_anon_client().auth.get_user(token)
    except Exception:
        raise APIError(401, "unauthorized", "Invalid or expired session token.")

    user = getattr(resp, "user", None)
    if user is None:
        raise APIError(401, "unauthorized", "Invalid or expired session token.")

    app_meta = getattr(user, "app_metadata", None) or {}
    user_meta = getattr(user, "user_metadata", None) or {}
    role = app_meta.get("role") or user_meta.get("role")
    if role not in ("sme", "bank"):
        raise APIError(403, "role_missing", "Authenticated user has no valid role assigned.")

    return Principal(user_id=user.id, role=role)


def require_sme(principal: Principal = Depends(get_current_user)) -> Principal:
    if principal.role != "sme":
        raise APIError(403, "forbidden", "This endpoint requires an SME account.")
    return principal


def require_bank(principal: Principal = Depends(get_current_user)) -> Principal:
    if principal.role != "bank":
        raise APIError(403, "forbidden", "This endpoint requires a bank account.")
    return principal
