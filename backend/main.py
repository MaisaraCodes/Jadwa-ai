"""
Jadwa.ai backend — FastAPI app factory (architecture.md §4).

Base path for all versioned routes is /api/v1 (set per-router). /health is the
only endpoint exempt from auth.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.errors import APIError, api_error_handler
from routers import documents


def create_app() -> FastAPI:
    app = FastAPI(title="Jadwa.ai API")

    origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(APIError, api_error_handler)
    app.include_router(documents.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
