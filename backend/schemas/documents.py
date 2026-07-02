"""
Response shape for POST /applications/{id}/documents.

architecture.md §4 specifies the wire response as:
    { document_id, filename, storage_url, status: "uploaded" }

This is a thin response DTO. The canonical persisted shape (document_id,
filename, storage_url, content_type) still lives in models.py::UploadedFile —
this DTO just adds the endpoint's `status` field and omits content_type from
the response body.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    storage_url: str
    status: Literal["uploaded"] = "uploaded"
