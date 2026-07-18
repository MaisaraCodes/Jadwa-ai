"""
The compiled LangGraph StateGraph — dispatch -> 4 agent nodes -> aggregate ->
application_builder (architecture.md §1, "Implementation note for whoever owns
the orchestrator").

document_intelligence_node is NOT part of this graph — architecture.md keeps it
outside, and core/orchestrator.py runs it just before the graph and feeds its
output into the initial state. application_builder_node IS in the graph, as the
terminal step: architecture.md §1's diagram is explicit about it
(`aggregate --> record --> builder --> END`), and it needs nothing the graph
doesn't already hold.
"""
from __future__ import annotations

import logging
import statistics

from langgraph.graph import END, START, StateGraph

from core.application_builder import application_builder_node
from core.supabase import get_service_client
from core.zatca import ZatcaParseError, ZatcaQRParser
from models import (
    ApplicationRecord,
    ApplicationState,
    DiscrepancyFlag,
    DocumentJSON,
    ForensicReport,
    MarketVerdict,
    RiskBaseline,
    WeaknessReport,
)
from nodes.devils_advocate.ledger import fetch_ledger_rows as fetch_devils_advocate_ledger_rows
from nodes.devils_advocate.ledger import split_by_type as split_ledger_rows_by_type
from nodes.devils_advocate.narrate import AdvocateContext, write_weakness_report
from nodes.devils_advocate.scoring import business_model_score, rank_weaknesses
from nodes.devils_advocate.signals import compute_all_signals
from nodes.forensic.explain import write_flag_descriptions
from nodes.forensic.matching import reconcile_against_ledger
from nodes.forensic.scoring import build_forensic_report
from nodes.saudi_market_oracle.retrieve import retrieve_market_chunks
from nodes.saudi_market_oracle.verdict import assemble_verdict

logger = logging.getLogger(__name__)

AGENT_RESULTS_TABLE = "agent_results"


def _persist_column(application_id: str, column: str, value: dict | list) -> None:
    """Each node's own UPDATE on `agent_results` (schema_mapping.md §2).

    Nodes persist their own column as soon as they finish, independently of
    the graph's in-memory state — that's what makes a partial run (one node
    crashes, others already succeeded) still leave usable data behind instead
    of losing everything.
    """
    try:
        get_service_client().table(AGENT_RESULTS_TABLE).update({column: value}).eq(
            "application_id", application_id
        ).execute()
    except Exception:
        logger.exception(
            "Failed to persist %s for application_id=%s", column, application_id
        )


def orchestrator_dispatch(state: ApplicationState) -> dict:
    """Fan-out point. Writes nothing — it exists only so the 4 parallel
    branches share one named node to fan out *from*, per architecture.md's
    diagram. There's no conditional routing here: `add_edge` (not
    `add_conditional_edges`) sends every run down all 4 branches, always."""
    return {}


def _check_zatca_qr(doc: DocumentJSON) -> list[DiscrepancyFlag]:
    """Decodes doc.zatca_qr_base64 (if present) and cross-checks it against the
    document's own OCR-extracted fields (vendor/extracted_amount) — the only
    ZATCA-adjacent data actually on hand (mock_open_banking_ledger has no
    invoice-level fields to compare against; see progress notes). `timestamp`
    is deliberately NOT compared: doc.date is a calendar date while the QR
    timestamp carries time-of-day, so they're never equal even for a genuine
    match."""
    if not doc.zatca_qr_base64:
        return []

    try:
        parser = ZatcaQRParser(doc.zatca_qr_base64)
        ledger_row = {
            "seller_name": doc.vendor,
            "invoice_total": doc.extracted_amount,
        }
        result = parser.validate_against_ledger(ledger_row)
    except ZatcaParseError as exc:
        return [DiscrepancyFlag(
            severity="medium",
            description=f"Document {doc.document_id}: unparseable ZATCA QR ({exc}).",
        )]

    flags: list[DiscrepancyFlag] = []
    for field_name, (qr_value, extracted_value) in result.mismatches.items():
        flags.append(DiscrepancyFlag(
            severity="high",
            description=(
                f"Document {doc.document_id}: ZATCA QR {field_name} ({qr_value!r}) "
                f"does not match extracted {field_name} ({extracted_value!r})."
            ),
        ))
    for err in result.errors:
        flags.append(DiscrepancyFlag(severity="medium", description=f"Document {doc.document_id}: {err}"))
    return flags


def forensic_accountant_node(state: ApplicationState) -> dict:
    """Two independent signal sources feed the report (architecture.md §1a):
    the ZATCA QR structural check (below, per-document) and ledger
    reconciliation (nodes/forensic/matching.py + scoring.py). Only the ledger
    check drives `reconciliation_rate` — that's specifically what
    schema_mapping.md Node 2 defines it as ("cross-reference extracted_documents
    against mock_open_banking_ledger"). ZATCA flags still fold into
    `overall_status` and `discrepancy_flags` since a forged QR is its own
    red flag even when the ledger otherwise reconciles.
    """
    documents = state.get("extracted_documents", [])
    cr_number = state["sme_profile"].cr_number

    zatca_flags: list[DiscrepancyFlag] = []
    for doc in documents:
        zatca_flags.extend(_check_zatca_qr(doc))

    matches, invoice_context = reconcile_against_ledger(cr_number, documents)
    ledger_report = build_forensic_report(
        matches,
        describe=lambda raw_flags: write_flag_descriptions(raw_flags, invoice_context),
    )

    discrepancy_flags = zatca_flags + ledger_report.discrepancy_flags
    if any(f.severity == "high" for f in discrepancy_flags):
        overall_status = "red"
    elif discrepancy_flags:
        overall_status = "yellow"
    else:
        overall_status = "green"

    report = ForensicReport(
        overall_status=overall_status,
        reconciliation_rate=ledger_report.reconciliation_rate,
        discrepancy_flags=discrepancy_flags,
    )
    _persist_column(state["application_id"], "forensic_report", report.model_dump(mode="json"))
    return {"forensic_report": report}


def devils_advocate_node(state: ApplicationState) -> dict:
    """Business-model critique (architecture.md §1, schema_mapping.md
    Node 3). Four deterministic Python signals
    (nodes/devils_advocate/signals.py) are graded from extracted_documents
    plus the SME's mock_open_banking_ledger rows, fetched in-node
    (CONVENTIONS.md rule 3) — this mirrors the forensic node's own ledger
    read, but Devil's Advocate needs BOTH debit and credit rows, so it uses
    its own fetch (nodes/devils_advocate/ledger.py) rather than forensic's
    debit-only one. scoring.py turns the signals into business_model_score
    plus the ranked weakness list; narrate.py (GPT-5.4 full) is the only LLM
    call in this node and writes text only — it never sets severity or the
    score.
    """
    documents = state.get("extracted_documents", [])
    sme_profile = state["sme_profile"]

    ledger_rows = fetch_devils_advocate_ledger_rows(sme_profile.cr_number)
    debit_rows, credit_rows = split_ledger_rows_by_type(ledger_rows)

    signals = compute_all_signals(
        debit_rows=debit_rows, credit_rows=credit_rows,
        documents=documents, sector=sme_profile.sector,
    )
    score = business_model_score(signals)
    ranked = rank_weaknesses(signals)

    narrative = write_weakness_report(
        ranked,
        AdvocateContext(company_name=sme_profile.company_name, sector=sme_profile.sector),
    )

    report = WeaknessReport(
        critical_weaknesses=narrative.critical_weaknesses,
        mitigation_suggestions=narrative.mitigation_suggestions,
        business_model_score=score,
    )
    _persist_column(state["application_id"], "weakness_report", report.model_dump(mode="json"))
    return {"weakness_report": report}


def saudi_market_oracle_node(state: ApplicationState) -> dict:
    """Retrieval-augmented market verdict (architecture.md §1,
    schema_mapping.md Node 4). pgvector cosine retrieval over
    market_knowledge_base keyed by sme_profile.sector / .district
    (nodes/saudi_market_oracle/retrieve.py — no sector WHERE clause; the
    corpus rows are general regulator reports with sector NULL), then ONE
    GPT-5.4 Mini call grounded strictly in the retrieved chunks
    (verdict.py). sources_cited is built deterministically in Python from
    the retrieved citations — the model never invents them. Any retrieval
    or LLM failure falls back to a deterministic honest MarketVerdict; this
    node never crashes the graph.
    """
    sme_profile = state["sme_profile"]
    sector = sme_profile.sector
    district = sme_profile.district

    try:
        rows = retrieve_market_chunks(sector, district)
    except Exception as exc:  # embed()/DB failures — fall back, never crash
        logger.warning("oracle: retrieval failed, using fallback verdict: %s", exc)
        rows = []

    verdict = assemble_verdict(rows, sector=sector, district=district)
    _persist_column(state["application_id"], "market_verdict", verdict.model_dump(mode="json"))
    return {"market_verdict": verdict}


# --- risk_sandbox_init_node coefficient heuristics -------------------------
# Pure-Python anchors for the RiskBaseline precompute (schema_mapping.md Node 5).
# These are deliberately simple, documented heuristics — Salman owns the realism
# pass. All are grounded loosely in the seeded invoice amounts (uniform 1.2k-18k,
# median ~6k; data/generate_synthetic_data.py). NO LLM, NO ledger read.
_NEUTRAL_DEFAULT_PROBABILITY = 0.10  # industry-ish anchor for a healthy SME
_THIN_FILE_DOC_COUNT = 3             # < this many docs = too little signal -> nudge risk up
_THIN_FILE_PENALTY = 0.05
_LOW_TOTAL_REF_SAR = 10_000.0        # total extracted value below this = weak signal -> nudge up
_LOW_TOTAL_PENALTY = 0.05
_VOL_MULTIPLIER_MIN, _VOL_MULTIPLIER_MAX = 0.8, 1.4
_BUFFER_REFERENCE_AMOUNT_SAR = 6_000.0   # median doc ~= this maps to the neutral buffer
_NEUTRAL_BUFFER_MONTHS = 3.0
_BUFFER_MIN_MONTHS, _BUFFER_MAX_MONTHS = 1.0, 6.0
_BASE_INTEREST_RATE = 0.08
_INTEREST_PER_VOL_UNIT = 0.02        # +2 rate points per unit of volatility above 1.0
_INTEREST_MIN, _INTEREST_MAX = 0.05, 0.12


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_risk_baseline(documents: list[DocumentJSON]) -> RiskBaseline:
    """Deterministic RiskBaseline precompute from extracted_documents alone
    (schema_mapping.md Node 5). Pure Python — no LLM, no ledger, no wall-clock,
    no randomness. Empty/None docs -> neutral defaults; never throws.
    """
    if not documents:
        return RiskBaseline(
            base_default_probability=_NEUTRAL_DEFAULT_PROBABILITY,
            revenue_volatility_multiplier=1.0,
            cash_buffer_months=_NEUTRAL_BUFFER_MONTHS,
            recommended_interest_rate=_BASE_INTEREST_RATE,
        )

    amounts = [float(d.extracted_amount) for d in documents]
    n = len(amounts)
    total = sum(amounts)
    mean = total / n

    # base_default_probability: anchor 0.10, nudged up for thin files / weak totals.
    default_probability = _NEUTRAL_DEFAULT_PROBABILITY
    if n < _THIN_FILE_DOC_COUNT:
        default_probability += _THIN_FILE_PENALTY
    if total < _LOW_TOTAL_REF_SAR:
        default_probability += _LOW_TOTAL_PENALTY
    default_probability = _clamp(default_probability, 0.0, 1.0)

    # revenue_volatility_multiplier: 1.0 + coefficient of variation, needs >=3 docs
    # for a meaningful spread; clamped to a sane band. Mean must be > 0 to divide.
    if n >= _THIN_FILE_DOC_COUNT and mean > 0:
        cv = statistics.pstdev(amounts) / mean
        volatility = _clamp(1.0 + cv, _VOL_MULTIPLIER_MIN, _VOL_MULTIPLIER_MAX)
    else:
        volatility = 1.0

    # cash_buffer_months: scale the neutral buffer by median doc size vs a reference.
    median = statistics.median(amounts)
    cash_buffer = _clamp(
        _NEUTRAL_BUFFER_MONTHS * median / _BUFFER_REFERENCE_AMOUNT_SAR,
        _BUFFER_MIN_MONTHS,
        _BUFFER_MAX_MONTHS,
    )

    # recommended_interest_rate: base + a premium for every unit of volatility > 1.0.
    interest_rate = _clamp(
        _BASE_INTEREST_RATE + _INTEREST_PER_VOL_UNIT * max(0.0, volatility - 1.0),
        _INTEREST_MIN,
        _INTEREST_MAX,
    )

    return RiskBaseline(
        base_default_probability=round(default_probability, 4),
        revenue_volatility_multiplier=round(volatility, 4),
        cash_buffer_months=round(cash_buffer, 4),
        recommended_interest_rate=round(interest_rate, 4),
    )


def risk_sandbox_init_node(state: ApplicationState) -> dict:
    """Precompute risk_baseline coefficients ONCE per application so the live
    Risk Sandbox never needs an LLM or a graph run (architecture.md §3,
    schema_mapping.md Node 5). Pure Python; reads only extracted_documents (the
    financial signal) — NOT the mock_open_banking_ledger (that's the forensic
    node's job, CONVENTIONS.md rule 3). Writes ONLY risk_baseline (rule 5).
    """
    documents = state.get("extracted_documents", [])
    baseline = compute_risk_baseline(documents)
    _persist_column(state["application_id"], "risk_baseline", baseline.model_dump(mode="json"))
    return {"risk_baseline": baseline}


def aggregate_results_node(state: ApplicationState) -> dict:
    """The one real (non-stub) node in this file: a deterministic merge, no
    LLM (architecture.md §1). LangGraph waits for all 4 incoming edges from
    the fan-out before calling this — no hand-written join/wait logic needed.
    """
    record = ApplicationRecord(
        application_id=state["application_id"],
        # Carried through from state UNCHANGED (spec rule: no lifecycle
        # transition here). The processing→review_ready advance happens in the
        # orchestrator after the graph completes, never inside this node.
        # "processing" is only the fallback when the key is absent (e.g. legacy
        # callers that predate status in ApplicationState).
        status=state.get("status", "processing"),
        sme_profile=state["sme_profile"],
        financing=state.get("financing"),
        extracted_documents=state.get("extracted_documents", []),
        forensic_report=state.get("forensic_report"),
        weakness_report=state.get("weakness_report"),
        market_verdict=state.get("market_verdict"),
        risk_baseline=state.get("risk_baseline"),
    )
    _persist_column(
        state["application_id"], "unified_application_record", record.model_dump(mode="json")
    )
    return {"unified_application_record": record}


def build_graph():
    graph = StateGraph(ApplicationState)

    graph.add_node("orchestrator_dispatch", orchestrator_dispatch)
    graph.add_node("forensic_accountant_node", forensic_accountant_node)
    graph.add_node("devils_advocate_node", devils_advocate_node)
    graph.add_node("saudi_market_oracle_node", saudi_market_oracle_node)
    graph.add_node("risk_sandbox_init_node", risk_sandbox_init_node)
    graph.add_node("aggregate_results_node", aggregate_results_node)
    graph.add_node("application_builder_node", application_builder_node)

    graph.add_edge(START, "orchestrator_dispatch")

    # Fan-out: 4 independent branches, all reading the same upstream state
    # and writing different keys (CONVENTIONS.md rule 5) — order between them
    # is not guaranteed and must not matter.
    graph.add_edge("orchestrator_dispatch", "forensic_accountant_node")
    graph.add_edge("orchestrator_dispatch", "devils_advocate_node")
    graph.add_edge("orchestrator_dispatch", "saudi_market_oracle_node")
    graph.add_edge("orchestrator_dispatch", "risk_sandbox_init_node")

    # Join: aggregate_results_node has 4 incoming edges, so LangGraph only
    # runs it once every branch above has completed.
    graph.add_edge("forensic_accountant_node", "aggregate_results_node")
    graph.add_edge("devils_advocate_node", "aggregate_results_node")
    graph.add_edge("saudi_market_oracle_node", "aggregate_results_node")
    graph.add_edge("risk_sandbox_init_node", "aggregate_results_node")

    # Terminal step: the Arabic PDF (architecture.md §1 — `record --> builder`).
    graph.add_edge("aggregate_results_node", "application_builder_node")
    graph.add_edge("application_builder_node", END)

    return graph.compile()


# Built once per process and reused — building a StateGraph is just wiring
# Python objects together, but there's no reason to redo it on every run.
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


__all__ = ["build_graph", "get_graph"]
