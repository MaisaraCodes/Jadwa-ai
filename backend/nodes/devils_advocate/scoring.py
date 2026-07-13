"""
Devil's Advocate — scoring + ranking layer (architecture.md §1). Deterministic
Python only (CONVENTIONS.md rule 1) — narrate.py may only add prose to
whichever signals land here, never re-grade them (mirrors
nodes/forensic/scoring.py::build_forensic_report).
"""
from __future__ import annotations

from nodes.devils_advocate.signals import SignalResult

MAX_WEAKNESSES = 4


def business_model_score(signals: list[SignalResult]) -> int:
    """100 minus every triggered signal's penalty, clamped to [0, 100]."""
    total_penalty = sum(signal.penalty for signal in signals if signal.triggered)
    return max(0, min(100, 100 - total_penalty))


def rank_weaknesses(signals: list[SignalResult], limit: int = MAX_WEAKNESSES) -> list[SignalResult]:
    """Triggered signals only, ranked by penalty (desc). Capped at `limit` —
    the rubric's "top 2-4 weaknesses" is simply the typical outcome of there
    being only four possible signals to trigger, not an enforced floor."""
    triggered = [signal for signal in signals if signal.triggered]
    ranked = sorted(triggered, key=lambda signal: signal.penalty, reverse=True)
    return ranked[:limit]


__all__ = ["MAX_WEAKNESSES", "business_model_score", "rank_weaknesses"]
