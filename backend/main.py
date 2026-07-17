"""
Jadwa.ai backend — FastAPI app factory (architecture.md §4).

Base path for all versioned routes is /api/v1 (set per-router). /health is the
only endpoint exempt from auth.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Built React frontend (frontend/dist). Present in production (deployment
# build step runs `npm run build`); absent in dev, where Vite serves the UI.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

from core.errors import APIError, api_error_handler
from routers import applications, bank, documents, profile, shared


def create_app() -> FastAPI:
    app = FastAPI(title="Jadwa.ai API")

    origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    # On Replit, requests come through the proxied dev domain — allow it automatically.
    replit_dev = os.environ.get("REPLIT_DEV_DOMAIN")
    if replit_dev:
        origins.append(f"https://{replit_dev}")
        origins.append(f"http://{replit_dev}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(APIError, api_error_handler)
    app.include_router(shared.router)
    app.include_router(profile.router)
    app.include_router(applications.router)
    app.include_router(bank.router)
    app.include_router(documents.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Production: serve the built SPA from the same server as the API.
    # API routes, /docs, /openapi.json and /health are registered above, so
    # they always win; everything else falls back to the SPA's index.html so
    # deep links like /bank/queue work.
    index_html = FRONTEND_DIST / "index.html"
    if index_html.is_file():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():

            class HashedAssets(StaticFiles):
                """Vite emits content-hashed filenames — cache them forever."""

                def file_response(self, *args, **kwargs):  # type: ignore[override]
                    response = super().file_response(*args, **kwargs)
                    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                    return response

            app.mount("/assets", HashedAssets(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            # Reserved backend namespaces must keep their own 404 semantics —
            # an unknown /api/... path must never return the SPA shell.
            first = full_path.split("/", 1)[0]
            if first in {"api", "docs", "redoc", "openapi.json", "health"}:
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = (FRONTEND_DIST / full_path).resolve()
            if (
                full_path
                and candidate.is_file()
                and candidate.is_relative_to(FRONTEND_DIST)
            ):
                return FileResponse(candidate)
            # Never cache the SPA shell — a stale index.html would reference
            # old hashed asset files after a redeploy.
            return FileResponse(
                index_html, headers={"Cache-Control": "no-cache"}
            )

    return app


app = create_app()
