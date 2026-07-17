"""
Tests for the Risk Sandbox endpoint (routers/bank.py):

    POST /api/v1/bank/applications/{application_id}/sandbox/recalculate
      body { deltas: ScenarioDeltas }
      -> 200 { projection: RiskProjection }

No network, no DB, no LLM: `require_bank` is overridden to inject a bank Principal,
and `get_service_client` is monkeypatched to a fake that returns a canned
agent_results row (or nothing). Mirrors tests/test_documents_upload.py.

These assert the wiring the endpoint promises — the role guard, the server-side
baseline load (client sends ONLY deltas), the 404 when the graph hasn't produced a
baseline, Pydantic body validation, determinism, and the <150ms perf target.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import routers.bank as bank_mod
from core.auth import Principal, get_current_user, require_bank
from main import create_app
from models import RiskProjection

APP_ID = "app-1"
URL = f"/api/v1/bank/applications/{APP_ID}/sandbox/recalculate"

# A realistic precomputed baseline (schema_mapping.md §2 Node 5 example).
BASELINE_JSON = {
    "base_default_probability": 0.12,
    "revenue_volatility_multiplier": 1.05,
    "cash_buffer_months": 3.2,
    "recommended_interest_rate": 0.08,
}


# --- fake service client ----------------------------------------------------
class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self._client = client
        self._table = table

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Result(self._client.select_data.get(self._table, []))


class FakeServiceClient:
    def __init__(self, *, agent_row=None):
        # agent_row=None -> no agent_results row exists at all.
        self.select_data = {"agent_results": [agent_row] if agent_row is not None else []}

    def table(self, name):
        return _Query(self, name)


# --- fixtures ---------------------------------------------------------------
def _make_client(fake_svc, monkeypatch, *, role="bank"):
    monkeypatch.setattr(bank_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    app.dependency_overrides[require_bank] = lambda: Principal(user_id="bank-1", role=role)
    return app


@pytest.fixture
def bank_client(monkeypatch):
    fake_svc = FakeServiceClient(
        agent_row={"application_id": APP_ID, "risk_baseline": BASELINE_JSON}
    )
    app = _make_client(fake_svc, monkeypatch)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _body(**deltas):
    return {"deltas": deltas}


# --- happy path -------------------------------------------------------------
def test_happy_path_returns_200_and_valid_projection(bank_client):
    resp = bank_client.post(URL, json=_body(revenue_growth=0.1, cost_increase=0.05))
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == {"projection"}  # response contains ONLY projection
    proj = body["projection"]

    # Validates against the canonical model shape.
    restored = RiskProjection.model_validate(proj)
    assert len(restored.months) == 12
    assert len(restored.cash_flow) == 12
    assert restored.risk_class in ("low", "medium", "high")
    assert 0.0 <= restored.risk_score <= 1.0
    assert isinstance(restored.summary_line, str) and restored.summary_line


def test_empty_deltas_object_uses_baseline_scenario(bank_client):
    # All deltas default to 0.0 (ScenarioDeltas) -> still a valid 200.
    resp = bank_client.post(URL, json={"deltas": {}})
    assert resp.status_code == 200
    assert len(resp.json()["projection"]["cash_flow"]) == 12


def test_response_does_not_leak_baseline(bank_client):
    resp = bank_client.post(URL, json=_body(revenue_growth=0.1))
    body = resp.json()
    # baseline never appears in the response, at any nesting level.
    assert "risk_baseline" not in body
    assert "base_default_probability" not in body["projection"]


# --- missing baseline (404) -------------------------------------------------
def test_no_agent_results_row_returns_404(monkeypatch):
    fake_svc = FakeServiceClient(agent_row=None)  # row absent entirely
    app = _make_client(fake_svc, monkeypatch)
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "risk_baseline_unavailable"


def test_null_risk_baseline_column_returns_404(monkeypatch):
    fake_svc = FakeServiceClient(agent_row={"application_id": APP_ID, "risk_baseline": None})
    app = _make_client(fake_svc, monkeypatch)
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "risk_baseline_unavailable"


def test_empty_dict_risk_baseline_returns_404(monkeypatch):
    # {} in the DB reads back as "not yet computed" (bank.py header comment).
    fake_svc = FakeServiceClient(agent_row={"application_id": APP_ID, "risk_baseline": {}})
    app = _make_client(fake_svc, monkeypatch)
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "risk_baseline_unavailable"


def test_malformed_risk_baseline_returns_500(monkeypatch):
    # Non-empty but invalid (missing required fields) -> validation failure.
    bad = {"application_id": APP_ID, "risk_baseline": {"base_default_probability": "not-a-number"}}
    fake_svc = FakeServiceClient(agent_row=bad)
    app = _make_client(fake_svc, monkeypatch)
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "risk_baseline_invalid"


# --- body validation --------------------------------------------------------
def test_missing_deltas_field_returns_422(bank_client):
    # `deltas` is required by SandboxRequest -> FastAPI/Pydantic 422.
    resp = bank_client.post(URL, json={})
    assert resp.status_code == 422


def test_malformed_delta_type_returns_422(bank_client):
    resp = bank_client.post(URL, json={"deltas": {"revenue_growth": "lots"}})
    assert resp.status_code == 422


# --- auth -------------------------------------------------------------------
def test_no_token_returns_401(monkeypatch):
    # No dependency override: the real require_bank -> get_current_user runs and
    # rejects the missing Authorization header with 401.
    fake_svc = FakeServiceClient(
        agent_row={"application_id": APP_ID, "risk_baseline": BASELINE_JSON}
    )
    monkeypatch.setattr(bank_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_sme_role_returns_403(monkeypatch):
    # Override the base auth dep to a valid SME principal; require_bank must 403 it.
    fake_svc = FakeServiceClient(
        agent_row={"application_id": APP_ID, "risk_baseline": BASELINE_JSON}
    )
    monkeypatch.setattr(bank_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: Principal(user_id="sme-1", role="sme")
    with TestClient(app) as c:
        resp = c.post(URL, json=_body(revenue_growth=0.1))
    app.dependency_overrides.clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


# --- determinism ------------------------------------------------------------
def test_determinism_three_identical_calls(bank_client):
    deltas = _body(revenue_growth=0.15, cost_increase=0.1, demand_shift=0.2, interest_rate=0.02)
    bodies = [bank_client.post(URL, json=deltas).json() for _ in range(3)]
    assert bodies[0] == bodies[1] == bodies[2]


# --- performance ------------------------------------------------------------
def test_endpoint_under_200ms(bank_client):
    deltas = _body(revenue_growth=0.1, cost_increase=0.05, demand_shift=0.2)
    durations_ms: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        resp = bank_client.post(URL, json=deltas)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        assert resp.status_code == 200
    mean_ms = sum(durations_ms) / len(durations_ms)
    max_ms = max(durations_ms)
    # Target is 150ms; 200ms allows CI headroom (fake DB is in-memory, so this is
    # really measuring FastAPI + engine overhead).
    assert mean_ms < 200.0, f"mean {mean_ms:.2f}ms exceeds 200ms"
    assert max_ms < 200.0, f"max {max_ms:.2f}ms exceeds 200ms"
