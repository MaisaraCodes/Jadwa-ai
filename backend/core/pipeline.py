"""
Shared LangGraph pipeline constants (architecture.md §1).

Lives here — not in routers/applications.py — so core/orchestrator.py can import
ALL_NODES without creating an applications <-> orchestrator import cycle (the
router needs to kick off the orchestrator; the orchestrator needs the node list).
"""
from __future__ import annotations

# The 6 nodes, in the order the LangGraph run reaches them (document intelligence
# first, then the 4-way fan-out, then the aggregate merge). /status reports
# nodes_completed as a prefix of this list.
ALL_NODES = [
    "document_intelligence_node",
    "forensic_accountant_node",
    "devils_advocate_node",
    "saudi_market_oracle_node",
    "risk_sandbox_init_node",
    "aggregate_results_node",
]

# Statuses that mean "the pipeline has already run for this application" —
# /status reports all nodes done and progress 1.0 for these without consulting
# the in-memory tracker (which won't have anything for an app processed in a
# previous server run).
TERMINAL_STATUSES = {"review_ready", "approved", "rejected", "more_info_needed"}

__all__ = ["ALL_NODES", "TERMINAL_STATUSES"]
