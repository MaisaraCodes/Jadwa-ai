"""
Bank dashboard (docs/API_CONTRACT.md) — role `bank`, no per-row ownership (any bank
account can see any application; only the role guard applies).

    GET  /api/v1/bank/applications                                REAL
    GET  /api/v1/bank/applications/{id}                           REAL
    POST /api/v1/bank/applications/{id}/sandbox/recalculate       STUB
    POST /api/v1/bank/applications/{id}/decision                  REAL

Node-output fields (forensic_report, weakness_report, market_verdict, risk_baseline,
forensic_status, business_model_score) are `null` until the Phase-2 LangGraph nodes
populate `agent_results` (`{}` in the DB reads back as "not yet computed" -> None).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.auth import Principal, require_bank
from core.errors import APIError
from core.supabase import get_service_client
from models import (
    ApplicationStatus,
    DocumentJSON,
    ForensicReport,
    MarketVerdict,
    RiskBaseline,
    RiskProjection,
    ScenarioDeltas,
    SMEProfile,
    WeaknessReport,
)

APPLICATIONS_TABLE = "applications"
APPLICATIONS_ID_COL = "id"
SME_PROFILES_TABLE = "sme_profiles"
AGENT_RESULTS_TABLE = "agent_results"

VALID_STATUSES = {
    "draft",
    "processing",
    "review_ready",
    "approved",
    "rejected",
    "more_info_needed",
}
SORTABLE_COLUMNS = {"updated_at", "created_at"}

DECISION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "request_info": "more_info_needed",
}

router = APIRouter(prefix="/api/v1/bank", tags=["bank"])


# --- response/request DTOs (shapes not already in models.py) ---------------
class BankApplicationListItem(BaseModel):
    application_id: str
    sme_name: str
    sector: str
    district: str
    submitted_at: str
    forensic_status: str | None
    business_model_score: int | None
    amount: float | None = None  # financing amount (SAR) — migration 004


class BankApplicationListResponse(BaseModel):
    applications: list[BankApplicationListItem]


class BankApplicationDetail(BaseModel):
    application_id: str
    status: ApplicationStatus
    sme_profile: SMEProfile
    extracted_documents: list[DocumentJSON]
    forensic_report: ForensicReport | None
    weakness_report: WeaknessReport | None
    market_verdict: MarketVerdict | None
    risk_baseline: RiskBaseline | None
    amount: float | None = None  # financing amount (SAR) — migration 004


class SandboxRequest(BaseModel):
    deltas: ScenarioDeltas


class SandboxResponse(BaseModel):
    projection: RiskProjection


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_info"]
    note: str | None = None


class DecisionResponse(BaseModel):
    status: ApplicationStatus


# --- helpers -----------------------------------------------------------------
def _get_application(svc, application_id: str) -> dict:
    res = (
        svc.table(APPLICATIONS_TABLE)
        .select("*")
        .eq(APPLICATIONS_ID_COL, application_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise APIError(404, "application_not_found", "No application with that id.")
    return rows[0]


def _get_agent_results(svc, application_id: str) -> dict:
    res = (
        svc.table(AGENT_RESULTS_TABLE)
        .select("*")
        .eq("application_id", application_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else {}


# --- GET /bank/applications ------------------------------------------------------
@router.get("/applications", response_model=BankApplicationListResponse)
async def list_bank_applications(
    status: str = Query(default="review_ready"),
    sort: str = Query(default="updated_at"),
    order: str = Query(default="desc"),
    principal: Principal = Depends(require_bank),
) -> BankApplicationListResponse:
    if status not in VALID_STATUSES:
        raise APIError(400, "invalid_status", f"'{status}' is not a valid application status.")
    sort_col = sort if sort in SORTABLE_COLUMNS else "updated_at"
    descending = order.lower() != "asc"

    svc = get_service_client()
    apps_res = (
        svc.table(APPLICATIONS_TABLE)
        .select(f"{APPLICATIONS_ID_COL},status,updated_at,sme_profile_id,amount")
        .eq("status", status)
        .order(sort_col, desc=descending)
        .execute()
    )
    apps = apps_res.data or []

    profile_ids = list({a["sme_profile_id"] for a in apps if a.get("sme_profile_id")})
    profiles: dict[str, dict] = {}
    if profile_ids:
        p_res = (
            svc.table(SME_PROFILES_TABLE)
            .select("id,company_name,sector,district")
            .in_("id", profile_ids)
            .execute()
        )
        profiles = {p["id"]: p for p in p_res.data or []}

    app_ids = [a[APPLICATIONS_ID_COL] for a in apps]
    agent_map: dict[str, dict] = {}
    if app_ids:
        ar_res = (
            svc.table(AGENT_RESULTS_TABLE)
            .select("application_id,forensic_report,weakness_report")
            .in_("application_id", app_ids)
            .execute()
        )
        agent_map = {r["application_id"]: r for r in ar_res.data or []}

    items = []
    for a in apps:
        profile = profiles.get(a["sme_profile_id"], {})
        ar = agent_map.get(a[APPLICATIONS_ID_COL], {})
        forensic_report = ar.get("forensic_report") or {}
        weakness_report = ar.get("weakness_report") or {}
        items.append(
            BankApplicationListItem(
                application_id=str(a[APPLICATIONS_ID_COL]),
                sme_name=profile.get("company_name", ""),
                sector=profile.get("sector", ""),
                district=profile.get("district", ""),
                submitted_at=str(a["updated_at"]),
                forensic_status=forensic_report.get("overall_status"),
                business_model_score=weakness_report.get("business_model_score"),
                amount=a.get("amount"),
            )
        )
    return BankApplicationListResponse(applications=items)


# --- GET /bank/applications/{id} --------------------------------------------------
@router.get("/applications/{application_id}", response_model=BankApplicationDetail)
async def get_bank_application(
    application_id: str,
    principal: Principal = Depends(require_bank),
) -> BankApplicationDetail:
    svc = get_service_client()
    app = _get_application(svc, application_id)

    profile_row = {}
    if app.get("sme_profile_id"):
        p_res = (
            svc.table(SME_PROFILES_TABLE)
            .select("*")
            .eq("id", app["sme_profile_id"])
            .limit(1)
            .execute()
        )
        rows = p_res.data or []
        profile_row = rows[0] if rows else {}

    sme_profile = SMEProfile(
        id=str(profile_row.get("id", app.get("sme_profile_id", ""))),
        company_name=profile_row.get("company_name", ""),
        cr_number=profile_row.get("cr_number", ""),
        sector=profile_row.get("sector", ""),
        district=profile_row.get("district", ""),
        user_id=profile_row.get("user_id"),
    )

    agent_results = _get_agent_results(svc, application_id)
    raw_extracted = agent_results.get("extracted_documents") or []
    raw_forensic = agent_results.get("forensic_report") or {}
    raw_weakness = agent_results.get("weakness_report") or {}
    raw_market = agent_results.get("market_verdict") or {}
    raw_risk = agent_results.get("risk_baseline") or {}

    return BankApplicationDetail(
        application_id=str(app[APPLICATIONS_ID_COL]),
        status=app["status"],
        sme_profile=sme_profile,
        extracted_documents=[DocumentJSON.model_validate(d) for d in raw_extracted],
        forensic_report=ForensicReport.model_validate(raw_forensic) if raw_forensic else None,
        weakness_report=WeaknessReport.model_validate(raw_weakness) if raw_weakness else None,
        market_verdict=MarketVerdict.model_validate(raw_market) if raw_market else None,
        risk_baseline=RiskBaseline.model_validate(raw_risk) if raw_risk else None,
        amount=app.get("amount"),
    )


# --- POST /bank/applications/{id}/sandbox/recalculate -----------------------------
# STUB — Phase-4 risk_calc_engine replaces this pure-Python placeholder math.
# The client sends ONLY deltas; the (currently-default, since risk_baseline isn't
# seeded yet) baseline never leaves the server.
_DEFAULT_BASELINE = RiskBaseline(
    base_default_probability=0.05,
    revenue_volatility_multiplier=1.0,
    cash_buffer_months=3.0,
    recommended_interest_rate=0.08,
)


def _recalculate(baseline: RiskBaseline, deltas: ScenarioDeltas) -> RiskProjection:
    months = [f"M{i + 1}" for i in range(12)]
    base_cash_flow = 100_000.0 * baseline.revenue_volatility_multiplier
    net_growth_pct = (
        deltas.revenue_growth - deltas.cost_increase - deltas.customer_churn + deltas.demand_shift
    )

    cash_flow: list[float] = []
    value = base_cash_flow
    for _ in months:
        value *= 1 + (net_growth_pct / 100)
        cash_flow.append(round(value, 2))

    risk_score = baseline.base_default_probability + (
        deltas.interest_rate
        + deltas.oil_price_sensitivity
        - deltas.revenue_growth
        + deltas.cost_increase
        + deltas.customer_churn
    ) / 100
    risk_score = max(0.0, min(1.0, round(risk_score, 4)))
    risk_class: Literal["low", "medium", "high"] = (
        "low" if risk_score < 0.15 else "medium" if risk_score < 0.35 else "high"
    )
    trend = "growth" if net_growth_pct >= 0 else "contraction"
    summary_line = f"Projected {risk_class} risk with a {trend} trend under the given scenario."

    return RiskProjection(
        months=months,
        cash_flow=cash_flow,
        risk_score=risk_score,
        risk_class=risk_class,
        summary_line=summary_line,
    )


@router.post("/applications/{application_id}/sandbox/recalculate", response_model=SandboxResponse)
async def recalculate_sandbox(
    application_id: str,
    body: SandboxRequest,
    principal: Principal = Depends(require_bank),
) -> SandboxResponse:
    svc = get_service_client()
    _get_application(svc, application_id)  # 404 if missing

    projection = _recalculate(_DEFAULT_BASELINE, body.deltas)
    return SandboxResponse(projection=projection)


# --- POST /bank/applications/{id}/decision -----------------------------------------
@router.post("/applications/{application_id}/decision", response_model=DecisionResponse)
async def decide_application(
    application_id: str,
    body: DecisionRequest,
    principal: Principal = Depends(require_bank),
) -> DecisionResponse:
    svc = get_service_client()
    _get_application(svc, application_id)  # 404 if missing

    new_status = DECISION_TO_STATUS[body.decision]
    svc.table(APPLICATIONS_TABLE).update({"status": new_status}).eq(
        APPLICATIONS_ID_COL, application_id
    ).execute()
    return DecisionResponse(status=new_status)
