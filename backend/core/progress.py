"""
In-memory run-progress tracker for the LangGraph orchestrator.

architecture.md is explicit that the hackathon build runs WITHOUT a LangGraph
checkpointer — in-memory state is fine, `agent_results` is the durable store for
final node output. This module is that in-memory state for IN-FLIGHT progress
only: it does not survive a process restart, and nothing depends on it doing so.

Assumes a single uvicorn worker process (the hosting note in CONVENTIONS.md /
API_CONTRACT.md — one Replit container, no multi-worker reload) so the dict
written by the background task is the same dict read by the polling /status
request.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_nodes_completed: dict[str, list[str]] = {}


def start(application_id: str) -> None:
    """Reset tracking for a fresh /process run."""
    with _lock:
        _nodes_completed[application_id] = []


def mark_done(application_id: str, node_name: str) -> None:
    with _lock:
        _nodes_completed.setdefault(application_id, []).append(node_name)


def get_nodes_completed(application_id: str) -> list[str]:
    with _lock:
        return list(_nodes_completed.get(application_id, []))


def clear(application_id: str) -> None:
    with _lock:
        _nodes_completed.pop(application_id, None)
