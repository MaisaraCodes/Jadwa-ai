"""
Tests for the document upload endpoint (routers/documents.py):

    POST /api/v1/applications/{application_id}/documents  (multipart: file)
      -> 201 { document_id, filename, storage_url, status: "uploaded" }

No network, no DB, no real Supabase: `require_sme` is overridden to inject a
Principal, and `get_service_client` is monkeypatched to a fake that records
Storage uploads/removes and table inserts (and can be told to fail). These
assert the wiring the endpoint promises — role+ownership gate, content-type /
size validation, canonical-column insert (file_url/file_type, id not
document_id), signed-URL response, and orphan cleanup when the DB insert fails
after a successful Storage upload.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

import routers.documents as docs_mod
from core.auth import Principal, require_sme
from main import create_app

APP_ID = "app-1"
PROFILE_ID = "prof-1"
USER_ID = "user-1"
URL = f"/api/v1/applications/{APP_ID}/documents"


# --- fake service client ----------------------------------------------------
class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self._client = client
        self._table = table
        self._op = "select"
        self._payload = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._op == "insert":
            self._client.inserts.append((self._table, self._payload))
            if self._client.fail_insert:
                raise RuntimeError("insert failed")
            return _Result([self._payload])
        return _Result(self._client.select_data.get(self._table, []))


class _Bucket:
    def __init__(self, client):
        self._c = client

    def upload(self, path, data, opts):
        if self._c.fail_upload:
            raise RuntimeError("upload failed")
        self._c.uploads.append((path, data, opts))

    def remove(self, paths):
        self._c.removes.extend(paths)

    def create_signed_url(self, path, ttl):
        return {"signedURL": f"https://signed.example/{path}?ttl={ttl}"}


class _Storage:
    def __init__(self, client):
        self._c = client

    def from_(self, bucket):
        return _Bucket(self._c)


class FakeServiceClient:
    def __init__(self, *, app_owner=PROFILE_ID, caller_profile=PROFILE_ID, app_exists=True):
        self.select_data = {
            "sme_profiles": [{"id": caller_profile}] if caller_profile else [],
            "applications": (
                [{"id": APP_ID, "sme_profile_id": app_owner}] if app_exists else []
            ),
        }
        self.uploads: list = []
        self.removes: list = []
        self.inserts: list = []
        self.fail_upload = False
        self.fail_insert = False
        self.storage = _Storage(self)

    def table(self, name):
        return _Query(self, name)


# --- fixtures ---------------------------------------------------------------
@pytest.fixture
def fake_svc():
    return FakeServiceClient()


@pytest.fixture
def client(fake_svc, monkeypatch):
    monkeypatch.setattr(docs_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    app.dependency_overrides[require_sme] = lambda: Principal(user_id=USER_ID, role="sme")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _pdf(name="my receipt.pdf", size=1024, content_type="application/pdf"):
    return {"file": (name, io.BytesIO(b"x" * size), content_type)}


# --- success ----------------------------------------------------------------
def test_upload_success_returns_201_and_signed_url(client, fake_svc):
    resp = client.post(URL, files=_pdf())
    assert resp.status_code == 201

    body = resp.json()
    assert body["status"] == "uploaded"
    assert body["filename"] == "my_receipt.pdf"  # sanitized
    assert body["document_id"]
    assert body["storage_url"].startswith("https://signed.example/")

    # exactly one object stored, one row inserted
    assert len(fake_svc.uploads) == 1
    assert len(fake_svc.inserts) == 1
    assert not fake_svc.removes  # nothing cleaned up on the happy path


def test_insert_uses_canonical_columns_not_dropped_ones(client, fake_svc):
    client.post(URL, files=_pdf())
    table, row = fake_svc.inserts[0]

    assert table == "application_documents"
    # PK is "id", not "document_id"; canonical file_url/file_type (CONVENTIONS.md)
    assert "id" in row and "document_id" not in row
    assert row["file_url"] and "storage_path" not in row
    assert row["file_type"] == "application/pdf" and "content_type" not in row
    assert row["application_id"] == APP_ID
    assert row["status"] == "uploaded"
    # persisted path is the stored object's path
    assert row["file_url"] == fake_svc.uploads[0][0]


# --- validation -------------------------------------------------------------
def test_unsupported_content_type_is_rejected(client):
    resp = client.post(URL, files=_pdf(name="notes.txt", content_type="text/plain"))
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported_media_type"


def test_oversized_file_is_rejected(client):
    resp = client.post(URL, files=_pdf(size=docs_mod.MAX_BYTES + 1))
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "file_too_large"


def test_empty_file_is_rejected(client):
    resp = client.post(URL, files=_pdf(size=0))
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "empty_file"


# --- ownership / existence --------------------------------------------------
def test_missing_application_returns_404(monkeypatch):
    svc = FakeServiceClient(app_exists=False)
    monkeypatch.setattr(docs_mod, "get_service_client", lambda: svc)
    app = create_app()
    app.dependency_overrides[require_sme] = lambda: Principal(user_id=USER_ID, role="sme")
    with TestClient(app) as c:
        resp = c.post(URL, files=_pdf())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "application_not_found"


def test_application_owned_by_another_sme_returns_403(monkeypatch):
    svc = FakeServiceClient(app_owner="someone-else")
    monkeypatch.setattr(docs_mod, "get_service_client", lambda: svc)
    app = create_app()
    app.dependency_overrides[require_sme] = lambda: Principal(user_id=USER_ID, role="sme")
    with TestClient(app) as c:
        resp = c.post(URL, files=_pdf())
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
    assert not svc.uploads  # never touched Storage


# --- failure / cleanup ------------------------------------------------------
def test_db_insert_failure_deletes_orphaned_object(client, fake_svc):
    fake_svc.fail_insert = True
    resp = client.post(URL, files=_pdf())

    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "db_error"
    # uploaded then cleaned up: no orphan left behind
    assert len(fake_svc.uploads) == 1
    assert fake_svc.removes == [fake_svc.uploads[0][0]]


def test_storage_upload_failure_returns_502_and_inserts_nothing(client, fake_svc):
    fake_svc.fail_upload = True
    resp = client.post(URL, files=_pdf())

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "storage_upload_failed"
    assert not fake_svc.inserts  # never recorded a row
