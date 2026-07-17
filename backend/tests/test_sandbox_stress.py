"""
Risk Sandbox STRESS / demo-safety suite (architecture.md §3, §4).

This is NOT product code — it's a stage safety net. Passing here means the
presenter can drag sliders for 7 minutes straight with no stutter, no error
banner, and a chart that lands in the same place every time.

DB-free / LLM-free like the rest of the suite: `get_service_client` is
monkeypatched to a fake returning a valid RiskBaseline dict, so what we measure
is the ENDPOINT + ENGINE, not Postgres. Production Postgres latency is a
monitoring concern, measured in prod — not here (that's the honest boundary).

No new deps: time.perf_counter + stdlib statistics only. No flaky tolerances —
if a machine is slow enough to fail these, we want to know (reproducibility
over accommodation).

Run with -s to see the perf receipts table:
    py -m pytest tests/test_sandbox_stress.py -s
"""
from __future__ import annotations

import math
import random
import statistics
import time

import pytest
from fastapi.testclient import TestClient

import routers.bank as bank_mod
from core.auth import Principal, require_bank
from core.risk_calc_engine import SLIDERS, recalculate
from main import create_app
from models import RiskBaseline, RiskProjection, ScenarioDeltas

APP_ID = "app-stress"
URL = f"/api/v1/bank/applications/{APP_ID}/sandbox/recalculate"

# A realistic precomputed baseline (schema_mapping.md §2 Node 5 example).
BASELINE_JSON = {
    "base_default_probability": 0.12,
    "revenue_volatility_multiplier": 1.05,
    "cash_buffer_months": 3.2,
    "recommended_interest_rate": 0.08,
}
BASELINE = RiskBaseline.model_validate(BASELINE_JSON)

SEED = 42


# ---------------------------------------------------------------------------
# Perf receipts — collected across tests, printed once at session teardown
# ---------------------------------------------------------------------------
_STATS: dict[str, dict[str, float]] = {}


def _percentile(sorted_ms: list[float], pct: float) -> float:
    """Nearest-rank percentile on an already-sorted list (no interpolation, no
    numpy). pct in [0, 100]."""
    if not sorted_ms:
        return 0.0
    k = max(0, min(len(sorted_ms) - 1, math.ceil(pct / 100.0 * len(sorted_ms)) - 1))
    return sorted_ms[k]


def _record(name: str, durations_ms: list[float], failures: int) -> dict[str, float]:
    ordered = sorted(durations_ms)
    row = {
        "count": float(len(durations_ms)),
        "mean": statistics.fmean(durations_ms) if durations_ms else 0.0,
        "p95": _percentile(ordered, 95),
        "p99": _percentile(ordered, 99),
        "max": max(durations_ms) if durations_ms else 0.0,
        "failures": float(failures),
    }
    _STATS[name] = row
    return row


@pytest.fixture(scope="session", autouse=True)
def _perf_summary():
    yield
    if not _STATS:
        return
    header = f"{'Test':<28} | {'count':>6} | {'mean(ms)':>9} | {'p95(ms)':>8} | {'p99(ms)':>8} | {'max(ms)':>8} | {'fails':>5}"
    line = "-" * len(header)
    print("\n\n=== Risk Sandbox stress — perf receipts ===")
    print(header)
    print(line)
    for name, r in _STATS.items():
        print(
            f"{name:<28} | {int(r['count']):>6} | {r['mean']:>9.3f} | {r['p95']:>8.3f} | "
            f"{r['p99']:>8.3f} | {r['max']:>8.3f} | {int(r['failures']):>5}"
        )
    print(line + "\n")


# ---------------------------------------------------------------------------
# Fake DB + client fixture (mirrors tests/test_sandbox_recalculate_endpoint.py)
# ---------------------------------------------------------------------------
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
        self.select_data = {"agent_results": [agent_row] if agent_row is not None else []}

    def table(self, name):
        return _Query(self, name)


@pytest.fixture
def bank_client(monkeypatch):
    fake_svc = FakeServiceClient(agent_row={"application_id": APP_ID, "risk_baseline": BASELINE_JSON})
    monkeypatch.setattr(bank_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    app.dependency_overrides[require_bank] = lambda: Principal(user_id="bank-1", role="bank")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _random_deltas(rng: random.Random) -> dict[str, float]:
    """Random-but-valid deltas, each within its slider's [min, max] band."""
    return {s.key: rng.uniform(s.min, s.max) for s in SLIDERS}


def _assert_valid_projection(payload: dict) -> RiskProjection:
    assert set(payload.keys()) == {"projection"}, f"response leaked keys: {payload.keys()}"
    proj = RiskProjection.model_validate(payload["projection"])
    assert len(proj.months) == 12
    assert len(proj.cash_flow) == 12
    assert all(math.isfinite(v) for v in proj.cash_flow), "non-finite cash_flow"
    assert 0.0 <= proj.risk_score <= 1.0, f"risk_score out of [0,1]: {proj.risk_score}"
    assert proj.risk_class in ("low", "medium", "high")
    return proj


# ===========================================================================
# Stress test A — slider spam (200 rapid random POSTs)
# ===========================================================================
def test_a_slider_spam_200_random_posts(bank_client):
    rng = random.Random(SEED)
    durations_ms: list[float] = []
    failures = 0

    for _ in range(200):
        deltas = _random_deltas(rng)
        t0 = time.perf_counter()
        resp = bank_client.post(URL, json={"deltas": deltas})
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        if resp.status_code != 200:
            failures += 1
            continue
        _assert_valid_projection(resp.json())

    row = _record("A: slider spam", durations_ms, failures)

    assert failures == 0, f"{failures}/200 requests failed"
    assert row["mean"] < 50.0, f"mean {row['mean']:.3f}ms exceeds 50ms"
    assert row["p95"] < 100.0, f"p95 {row['p95']:.3f}ms exceeds 100ms"
    assert row["p99"] < 150.0, f"p99 {row['p99']:.3f}ms exceeds 150ms"


# ===========================================================================
# Stress test B — determinism at scale (200 identical POSTs, byte-identical)
# ===========================================================================
def test_b_determinism_200_identical_posts(bank_client):
    body = {
        "deltas": {
            "revenue_growth": 0.12,
            "cost_increase": 0.18,
            "customer_churn": 0.07,
            "demand_shift": -0.25,
            "interest_rate": 0.03,
            "oil_price_sensitivity": 0.20,
        }
    }
    first = bank_client.post(URL, json=body).content
    for _ in range(199):
        assert bank_client.post(URL, json=body).content == first, "non-deterministic response"


# ===========================================================================
# Stress test C — extreme values per slider (min, max, min-eps, max+eps)
# ===========================================================================
def test_c_extreme_values_per_slider(bank_client):
    eps = 0.001
    for s in SLIDERS:
        for value in (s.min, s.max, s.min - eps, s.max + eps):
            # every other slider held at 0; only this one pushed to the edge
            deltas = {other.key: 0.0 for other in SLIDERS}
            deltas[s.key] = value
            resp = bank_client.post(URL, json={"deltas": deltas})
            assert resp.status_code == 200, f"{s.key}={value} returned {resp.status_code}"
            _assert_valid_projection(resp.json())


# ===========================================================================
# Stress test D — all sliders extreme simultaneously (max combo, min combo)
# ===========================================================================
def test_d_all_sliders_extreme_combo(bank_client):
    for pick in ("max", "min"):
        deltas = {s.key: (s.max if pick == "max" else s.min) for s in SLIDERS}
        resp = bank_client.post(URL, json={"deltas": deltas})
        assert resp.status_code == 200, f"all-{pick} combo returned {resp.status_code}"
        _assert_valid_projection(resp.json())


# ===========================================================================
# Stress test E — malformed payloads fail cleanly (never crash)
# ===========================================================================
def test_e_missing_deltas_field_is_422(bank_client):
    resp = bank_client.post(URL, json={})
    assert resp.status_code == 422


def test_e_non_numeric_delta_is_422(bank_client):
    resp = bank_client.post(URL, json={"deltas": {"revenue_growth": "lots"}})
    assert resp.status_code == 422


def test_e_extra_top_level_field_is_ignored_200(bank_client):
    # Pydantic v2 ignores unknown fields by default -> the extra key is dropped
    # and the request still succeeds. If this ever starts 422-ing, the model
    # gained `extra="forbid"` and the frontend contract must be revisited.
    resp = bank_client.post(URL, json={"deltas": {"revenue_growth": 0.1}, "unknown_field": "ignored"})
    assert resp.status_code == 200, "extra top-level field should be ignored, not rejected"
    _assert_valid_projection(resp.json())


def test_e_validation_error_envelope_is_fastapi_default(bank_client):
    # HONEST CHECK: request-validation (422) errors use FastAPI's built-in
    # {"detail": [...]} shape, NOT the custom {"error": {code, message}} envelope
    # (that handler is registered only for APIError — see main.py). APIError-driven
    # failures like the 404 below DO use the custom envelope.
    resp = bank_client.post(URL, json={})
    assert resp.status_code == 422
    assert "detail" in resp.json()
    assert "error" not in resp.json()


def test_e_apierror_uses_custom_envelope(monkeypatch):
    # Contrast: a missing baseline (APIError 404) DOES follow {error:{code,message}}.
    fake_svc = FakeServiceClient(agent_row=None)
    monkeypatch.setattr(bank_mod, "get_service_client", lambda: fake_svc)
    app = create_app()
    app.dependency_overrides[require_bank] = lambda: Principal(user_id="bank-1", role="bank")
    with TestClient(app) as c:
        resp = c.post(URL, json={"deltas": {"revenue_growth": 0.1}})
    app.dependency_overrides.clear()
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}
    assert body["error"]["code"] == "risk_baseline_unavailable"


# ===========================================================================
# Stress test F — engine-only micro-benchmark (10,000 calls, no HTTP)
# ===========================================================================
def test_f_engine_micro_benchmark_10k():
    rng = random.Random(SEED)
    durations_ms: list[float] = []

    for _ in range(10_000):
        deltas = ScenarioDeltas(**_random_deltas(rng))
        t0 = time.perf_counter()
        proj = recalculate(BASELINE, deltas)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        # cheap invariants — full validation would dominate the timing loop,
        # so only spot-check finiteness here.
        assert math.isfinite(proj.cash_flow[-1])

    row = _record("F: engine 10k", durations_ms, 0)

    assert row["mean"] < 1.0, f"engine mean {row['mean']:.4f}ms exceeds 1ms"
    assert row["p99"] < 5.0, f"engine p99 {row['p99']:.4f}ms exceeds 5ms"
