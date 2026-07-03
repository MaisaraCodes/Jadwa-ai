"""
Supabase client factories.

Two clients, on purpose:
  - service-role: bypasses RLS. Used for Storage writes and inserting the
    application_documents row from trusted backend code. NEVER expose this key
    to the frontend.
  - anon: used only to validate a caller's Supabase JWT (auth.get_user).

Env vars (add to backend/.env and .env.example):
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  SUPABASE_ANON_KEY
"""
from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


@lru_cache(maxsize=1)
def get_service_client() -> Client:
    """Trusted backend client. Bypasses RLS — keep the key server-side only."""
    return create_client(_require("SUPABASE_URL"), _require("SUPABASE_SERVICE_ROLE_KEY"))


@lru_cache(maxsize=1)
def get_anon_client() -> Client:
    """Anon client, used only to resolve a JWT into a user via auth.get_user()."""
    return create_client(_require("SUPABASE_URL"), _require("SUPABASE_ANON_KEY"))
