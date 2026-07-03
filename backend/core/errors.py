"""
Uniform error surface for the whole API (CONVENTIONS.md):

    { "error": { "code": string, "message": string } }

Raise APIError anywhere; the registered handler renders it with the right
HTTP status. Register once in main.py:

    from core.errors import APIError, api_error_handler
    app.add_exception_handler(APIError, api_error_handler)
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
