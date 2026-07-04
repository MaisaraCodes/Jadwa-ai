"""
The compiled LangGraph StateGraph — dispatch -> 4 agent nodes -> aggregate
(architecture.md §1, "Implementation note for whoever owns the orchestrator").

Only the SHAPE is this ticket's job. The 4 middle nodes below are STUBS: each
one's real owner replaces the body of their function (the reconciliation
math, the LLM call, the pgvector lookup...) but keeps the function's name,
its read/write keys on ApplicationState, and its position in the graph
exactly as wired here. document_intelligence_node and
application_builder_node are separate tickets and are NOT part of this
graph — see core/orchestrator.py for where they slot in around it.
"""
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from core.supabase import get_service_client
from models import (
    ApplicationRecord,
    ApplicationState,
    ForensicReport,
    MarketVerdict,
    RiskBaseline,
    WeaknessReport,
)

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


def forensic_accountant_node(state: ApplicationState) -> dict:
    # TODO(owner: forensic accountant, architecture.md §1a): reconcile
    # extracted_documents against mock_open_banking_ledger (queried in-node,
    # filtered by sme_profile.cr_number) in plain Python; the LLM only writes
    # each DiscrepancyFlag's description text.
    report = ForensicReport(overall_status="green", reconciliation_rate=1.0, discrepancy_flags=[])
    _persist_column(state["application_id"], "forensic_report", report.model_dump(mode="json"))
    return {"forensic_report": report}


def devils_advocate_node(state: ApplicationState) -> dict:
    # TODO(owner: devil's advocate): real GPT-5.4 critique of sme_profile +
    # extracted_documents.
    report = WeaknessReport(critical_weaknesses=[], mitigation_suggestions=[], business_model_score=50)
    _persist_column(state["application_id"], "weakness_report", report.model_dump(mode="json"))
    return {"weakness_report": report}


def saudi_market_oracle_node(state: ApplicationState) -> dict:
    # TODO(owner: market oracle): real pgvector similarity search over
    # market_knowledge_base, keyed by sme_profile.sector / .district.
    verdict = MarketVerdict(
        sector_trend="stable", district_saturation="medium", oracle_insight="", sources_cited=[]
    )
    _persist_column(state["application_id"], "market_verdict", verdict.model_dump(mode="json"))
    return {"market_verdict": verdict}


def risk_sandbox_init_node(state: ApplicationState) -> dict:
    # TODO(owner: risk sandbox): real coefficient precompute from
    # extracted_documents. Pure Python, no LLM — this just needs a plausible
    # placeholder so aggregate_results_node has something to merge.
    baseline = RiskBaseline(
        base_default_probability=0.1,
        revenue_volatility_multiplier=1.0,
        cash_buffer_months=1.0,
        recommended_interest_rate=0.08,
    )
    _persist_column(state["application_id"], "risk_baseline", baseline.model_dump(mode="json"))
    return {"risk_baseline": baseline}


def aggregate_results_node(state: ApplicationState) -> dict:
    """The one real (non-stub) node in this file: a deterministic merge, no
    LLM (architecture.md §1). LangGraph waits for all 4 incoming edges from
    the fan-out before calling this — no hand-written join/wait logic needed.
    """
    record = ApplicationRecord(
        application_id=state["application_id"],
        # Still "processing" at this instant: the outer app-level status only
        # advances once /submit is called (routers/applications.py) — this
        # record's own status field mirrors that, not the graph's completion.
        status="processing",
        sme_profile=state["sme_profile"],
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

    graph.add_edge("aggregate_results_node", END)

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
