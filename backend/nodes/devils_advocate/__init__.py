"""
Devil's Advocate node package (architecture.md §1, schema_mapping.md Node 3).

    ledger.py    fetch_ledger_rows / split_by_type — Postgres, in-node (CONVENTIONS.md rule 3)
    signals.py   pure-Python weakness signals (CONVENTIONS.md rule 1)
    scoring.py   business_model_score + ranking, deterministic
    narrate.py   the ONLY LLM call — writes weakness/mitigation text (GPT-5.4 full)

core/graph.py::devils_advocate_node composes these directly (mirrors how
forensic_accountant_node composes nodes/forensic/*) — this __init__ just
re-exports the pieces for tests and any future caller.
"""
from __future__ import annotations

from nodes.devils_advocate.ledger import fetch_ledger_rows, split_by_type
from nodes.devils_advocate.narrate import AdvocateContext, WeaknessNarrative, write_weakness_report
from nodes.devils_advocate.scoring import business_model_score, rank_weaknesses
from nodes.devils_advocate.signals import SignalResult, compute_all_signals

__all__ = [
    "fetch_ledger_rows",
    "split_by_type",
    "compute_all_signals",
    "SignalResult",
    "business_model_score",
    "rank_weaknesses",
    "AdvocateContext",
    "WeaknessNarrative",
    "write_weakness_report",
]
