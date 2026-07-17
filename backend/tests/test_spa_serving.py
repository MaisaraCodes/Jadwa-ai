"""
Tests for production SPA serving in main.py.

The SPA catch-all is registered only when frontend/dist/index.html exists.
These tests point FRONTEND_DIST at a temp dist so they are independent of
whether a real frontend build is present, and prove:
- deep links serve index.html (with no-cache) so client routing works
- real files under dist are served directly
- unknown /api/... paths keep backend 404 semantics (never the SPA shell)
- path traversal outside dist is not possible
- without a dist build, no catch-all exists (dev mode unchanged)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main as main_module


@pytest.fixture()
def spa_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>SPA SHELL</body></html>")
    (dist / "favicon.svg").write_text("<svg></svg>")
    (dist / "assets" / "index-abc123.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("outside dist")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", dist)
    return TestClient(main_module.create_app())


class TestSpaServing:
    def test_root_serves_index_html(self, spa_client):
        r = spa_client.get("/")
        assert r.status_code == 200
        assert "SPA SHELL" in r.text
        assert r.headers["cache-control"] == "no-cache"

    def test_deep_link_serves_index_html(self, spa_client):
        r = spa_client.get("/bank/queue")
        assert r.status_code == 200
        assert "SPA SHELL" in r.text

    def test_real_static_file_served(self, spa_client):
        r = spa_client.get("/favicon.svg")
        assert r.status_code == 200
        assert r.text == "<svg></svg>"

    def test_hashed_assets_cached_immutably(self, spa_client):
        r = spa_client.get("/assets/index-abc123.js")
        assert r.status_code == 200
        assert "immutable" in r.headers["cache-control"]

    def test_unknown_api_route_is_404_not_spa(self, spa_client):
        r = spa_client.get("/api/v1/definitely-not-a-route")
        assert r.status_code == 404
        assert "SPA SHELL" not in r.text

    def test_health_still_json(self, spa_client):
        r = spa_client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_docs_and_openapi_still_work(self, spa_client):
        assert spa_client.get("/docs").status_code == 200
        assert spa_client.get("/openapi.json").status_code == 200

    def test_path_traversal_returns_shell_not_file(self, spa_client):
        r = spa_client.get("/..%2Fsecret.txt")
        assert r.status_code in (200, 404)
        assert "outside dist" not in r.text


class TestDevModeWithoutDist:
    def test_no_catch_all_without_build(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main_module, "FRONTEND_DIST", tmp_path / "missing")
        client = TestClient(main_module.create_app())
        assert client.get("/bank/queue").status_code == 404
        assert client.get("/health").status_code == 200
