"""
Shared endpoints — any authenticated principal, either role.

    GET /api/v1/me   -> { user_id, role, display_name }

REAL — reads straight off the validated Supabase JWT (core/auth.py); no DB round-trip.
`display_name` falls back to `user_metadata.display_name`, then email, then user_id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.auth import Principal, get_current_user

router = APIRouter(prefix="/api/v1", tags=["shared"])


class MeResponse(BaseModel):
    user_id: str
    role: str
    display_name: str


@router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=principal.user_id,
        role=principal.role,
        display_name=principal.display_name or principal.email or principal.user_id,
    )
