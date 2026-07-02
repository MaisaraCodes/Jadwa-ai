"""
Jadwa.ai — canonical data contract (SINGLE SOURCE OF TRUTH).

Every LangGraph node, every FastAPI endpoint, and the `agent_results` JSONB
store use THESE models. Do not redefine these shapes anywhere else. If a shape
must change, change it here and update /docs/schema_mapping.md in the SAME commit.

DB mapping (see schema_mapping.md — each JSONB column is a 1:1 dump of one model):
    extracted_documents         -> list[DocumentJSON]
    forensic_report             -> ForensicReport
    weakness_report             -> WeaknessReport
    market_verdict              -> MarketVerdict
    risk_baseline               -> RiskBaseline
    unified_application_record  -> ApplicationRecord

Persist with `model.model_dump(mode="json")`; load with `Model.model_validate(row)`.

Requires: pydantic>=2
"""
from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared enums / literals
# ---------------------------------------------------------------------------
Role = Literal["sme", "bank"]

# Status lifecycle (architecture.md §4):
# draft -> processing -> review_ready -> submitted -> approved | rejected | info_requested
ApplicationStatus = Literal[
    "draft",
    "processing",
    "review_ready",
    "submitted",
    "approved",
    "rejected",
    "info_requested",
]

ForensicStatus = Literal["green", "yellow", "red"]
Severity = Literal["high", "medium", "low"]
RiskClass = Literal["low", "medium", "high"]
SectorTrend = Literal["growing", "stable", "declining"]
Saturation = Literal["low", "medium", "high"]
DocumentType = Literal["zatca_receipt", "invoice", "bank_statement", "contract", "other"]


# ---------------------------------------------------------------------------
# Core profile & uploads
# ---------------------------------------------------------------------------
class SMEProfile(BaseModel):
    sme_id: str
    name: str
    cr_number: str  # Commercial Registration number — KEYS the ledger lookup in the forensic node
    sector: str
    district: str
    established_year: int | None = None
    backstory: str | None = None  # demo colour only; not used by any agent


class UploadedFile(BaseModel):
    document_id: str
    filename: str
    storage_url: str  # Supabase Storage URL
    content_type: str


# ---------------------------------------------------------------------------
# Node 1 — document_intelligence_node  ->  extracted_documents  (GPT-5.4 vision)
# ---------------------------------------------------------------------------
class DocumentJSON(BaseModel):
    document_id: str
    type: DocumentType = "other"
    vendor: str | None = None
    extracted_amount: float
    currency: str = "SAR"
    date: date
    line_items: list[str] = Field(default_factory=list)
    # Parsed OFFLINE from the invoice's ZATCA TLV QR (NOT a ZATCA API call). None if absent.
    zatca_verification_hash: str | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Node 2 — forensic_accountant_node  ->  forensic_report  (GPT-5.4 Mini)
# Reconciliation math is PYTHON; the LLM only writes discrepancy `description` text.
# ---------------------------------------------------------------------------
class DiscrepancyFlag(BaseModel):
    severity: Severity
    description: str


class ForensicReport(BaseModel):
    overall_status: ForensicStatus
    reconciliation_rate: float = Field(ge=0.0, le=1.0)
    discrepancy_flags: list[DiscrepancyFlag] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Node 3 — devils_advocate_node  ->  weakness_report  (GPT-5.4)
# ---------------------------------------------------------------------------
class WeaknessReport(BaseModel):
    critical_weaknesses: list[str] = Field(default_factory=list)
    mitigation_suggestions: list[str] = Field(default_factory=list)
    business_model_score: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# Node 4 — saudi_market_oracle_node  ->  market_verdict  (GPT-5.4 Mini + text-embedding-3-large)
# ---------------------------------------------------------------------------
class MarketVerdict(BaseModel):
    sector_trend: SectorTrend
    district_saturation: Saturation
    oracle_insight: str
    sources_cited: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Node 5 — risk_sandbox_init_node  ->  risk_baseline  (pure Python, no LLM)
# Precomputed once so the live sandbox never calls a model.
# ---------------------------------------------------------------------------
class RiskBaseline(BaseModel):
    base_default_probability: float = Field(ge=0.0, le=1.0)
    revenue_volatility_multiplier: float
    cash_buffer_months: float
    recommended_interest_rate: float


# ---------------------------------------------------------------------------
# aggregate_results_node  ->  unified_application_record  (deterministic merge)
# This is the ENTIRE payload the bank dashboard reads in one call.
# ---------------------------------------------------------------------------
class ApplicationRecord(BaseModel):
    application_id: str
    status: ApplicationStatus
    sme_profile: SMEProfile
    extracted_documents: list[DocumentJSON] = Field(default_factory=list)
    forensic_report: ForensicReport | None = None
    weakness_report: WeaknessReport | None = None
    market_verdict: MarketVerdict | None = None
    risk_baseline: RiskBaseline | None = None


# ---------------------------------------------------------------------------
# Risk Sandbox — NON-LLM, lives OUTSIDE the LangGraph (architecture.md §3).
# Pure function:  recalculate(baseline: RiskBaseline, deltas: ScenarioDeltas) -> RiskProjection
# Exposed at POST /api/v1/bank/applications/{id}/sandbox/recalculate.
# The client sends ONLY deltas; the baseline never leaves the server.
# ---------------------------------------------------------------------------
class ScenarioDeltas(BaseModel):
    revenue_growth: float = 0.0
    cost_increase: float = 0.0
    customer_churn: float = 0.0
    demand_shift: float = 0.0
    interest_rate: float = 0.0
    oil_price_sensitivity: float = 0.0


class RiskProjection(BaseModel):
    months: list[str]          # 12 month labels
    cash_flow: list[float]     # 12 projected values, same order as `months`
    risk_score: float
    risk_class: RiskClass
    summary_line: str


# ---------------------------------------------------------------------------
# LangGraph state (architecture.md §2)
# One typed key per node output — never a shared blob. This is what lets
# aggregate_results_node merge cleanly with no conflict-resolution logic.
# ---------------------------------------------------------------------------
class ApplicationState(TypedDict):
    application_id: str
    sme_profile: SMEProfile
    raw_documents: list[UploadedFile]

    # written by document_intelligence_node
    extracted_documents: list[DocumentJSON]

    # written by the 4 parallel agent nodes
    forensic_report: ForensicReport | None
    weakness_report: WeaknessReport | None
    market_verdict: MarketVerdict | None
    risk_baseline: RiskBaseline | None

    # written by aggregate_results_node
    unified_application_record: ApplicationRecord | None


__all__ = [
    "Role",
    "ApplicationStatus",
    "ForensicStatus",
    "Severity",
    "RiskClass",
    "SectorTrend",
    "Saturation",
    "DocumentType",
    "SMEProfile",
    "UploadedFile",
    "DocumentJSON",
    "DiscrepancyFlag",
    "ForensicReport",
    "WeaknessReport",
    "MarketVerdict",
    "RiskBaseline",
    "ApplicationRecord",
    "ScenarioDeltas",
    "RiskProjection",
    "ApplicationState",
]
