"""
Node tests for saudi_market_oracle_node (core/graph.py) — mirrors
tests/test_devils_advocate_node.py: monkeypatch the retrieval and the LLM
wrapper so everything stays DB-free and LLM-free, then assert the node
writes ONLY market_verdict and produces a valid MarketVerdict, with the
fallback contract honored on every failure mode.
"""
from __future__ import annotations

import json

import pytest

import core.graph as graph_module
import nodes.saudi_market_oracle.verdict as verdict_module
from core.graph import saudi_market_oracle_node
from models import MarketVerdict, SMEProfile
from nodes.saudi_market_oracle.verdict import (
    assemble_verdict,
    build_sources_cited,
    prettify_citation,
)


def make_sme_profile(**overrides) -> SMEProfile:
    defaults = dict(
        id="sme-1", company_name="Rawad Logistics", cr_number="1010482913",
        sector="logistics", district="Al-Kharj",
    )
    defaults.update(overrides)
    return SMEProfile(**defaults)


def make_row(citation: str, content: str = "نمو قطاع الخدمات اللوجستية", agency: str = "Monshaat", score: float = 0.82) -> dict:
    return {"content": content, "source_agency": agency, "citation": citation, "score": score}


ROWS = [
    make_row("Monshaat — Sme Report 2024\u2060"),
    make_row("Sama — Annual Financial Stability Report 2024", agency="Sama"),
    make_row("Monshaat — Sme Report 2024"),  # duplicate of row 1 after cleanup
    make_row("Gastat — Business Census 2024", agency="Gastat"),
]

GOOD_REPLY = json.dumps({
    "sector_trend": "growing",
    "district_saturation": "low",
    "oracle_insight": "Monsha'at and SAMA reports indicate strong logistics growth.",
})


def make_state(**overrides) -> dict:
    state = {
        "application_id": "app-1", "sme_profile": make_sme_profile(),
        "raw_documents": [], "extracted_documents": [],
    }
    state.update(overrides)
    return state


@pytest.fixture(autouse=True)
def no_persist(monkeypatch):
    monkeypatch.setattr(graph_module, "_persist_column", lambda *a, **k: None)


class TestSaudiMarketOracleNode:
    def test_happy_path_produces_valid_market_verdict(self, monkeypatch):
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: ROWS)
        monkeypatch.setattr(verdict_module, "complete", lambda *a, **k: GOOD_REPLY)

        result = saudi_market_oracle_node(make_state())

        assert set(result.keys()) == {"market_verdict"}
        verdict = result["market_verdict"]
        assert isinstance(verdict, MarketVerdict)
        assert verdict.sector_trend == "growing"
        assert verdict.district_saturation == "low"
        assert "SAMA" in verdict.oracle_insight
        # Persist contract: round-trips through model_dump(mode="json").
        assert MarketVerdict.model_validate(verdict.model_dump(mode="json")) == verdict

    def test_sources_cited_deduped_prettified_and_never_from_llm(self, monkeypatch):
        # The LLM tries to smuggle in its own citations — they must be ignored.
        reply = json.dumps({
            "sector_trend": "stable",
            "district_saturation": "medium",
            "oracle_insight": "Stable outlook.",
            "sources_cited": ["Fabricated Source 2030"],
        })
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: ROWS)
        monkeypatch.setattr(verdict_module, "complete", lambda *a, **k: reply)

        verdict = saudi_market_oracle_node(make_state())["market_verdict"]

        assert verdict.sources_cited == [
            "Monsha'at — Sme Report 2024",       # deduped (rows 1 & 3), U+2060 stripped
            "SAMA — Annual Financial Stability Report 2024",
            "GASTAT — Business Census 2024",
        ]
        assert "Fabricated Source 2030" not in verdict.sources_cited

    def test_empty_retrieval_falls_back_deterministically(self, monkeypatch):
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: [])

        def fail(*a, **k):  # the LLM must not even be called on empty retrieval
            raise AssertionError("complete() must not be called when retrieval is empty")

        monkeypatch.setattr(verdict_module, "complete", fail)

        verdict = saudi_market_oracle_node(make_state())["market_verdict"]
        assert verdict.sector_trend == "stable"
        assert verdict.district_saturation == "medium"
        assert "insufficient" in verdict.oracle_insight.lower()
        assert verdict.sources_cited == []

    def test_retrieval_exception_falls_back_not_crash(self, monkeypatch):
        def boom(s, d):
            raise RuntimeError("DB unreachable")

        monkeypatch.setattr(graph_module, "retrieve_market_chunks", boom)
        verdict = saudi_market_oracle_node(make_state())["market_verdict"]
        assert verdict.sector_trend == "stable"
        assert verdict.sources_cited == []

    def test_llm_error_falls_back_with_retrieved_citations(self, monkeypatch):
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: ROWS)

        def boom(*a, **k):
            raise verdict_module.LLMError("forced failure")

        monkeypatch.setattr(verdict_module, "complete", boom)

        verdict = saudi_market_oracle_node(make_state())["market_verdict"]
        assert verdict.sector_trend == "stable"
        assert verdict.district_saturation == "medium"
        assert "insufficient" in verdict.oracle_insight.lower()
        # Fallback still cites what WAS retrieved.
        assert len(verdict.sources_cited) == 3

    @pytest.mark.parametrize("bad_reply", [
        "not json at all",
        '{"sector_trend": "sideways", "district_saturation": "medium", "oracle_insight": "x"}',
        '{"district_saturation": "medium"}',  # missing keys
        '{"sector_trend": "growing", "district_saturation": "extreme", "oracle_insight": "x"}',
    ])
    def test_malformed_or_invalid_json_falls_back(self, monkeypatch, bad_reply):
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: ROWS)
        monkeypatch.setattr(verdict_module, "complete", lambda *a, **k: bad_reply)

        verdict = saudi_market_oracle_node(make_state())["market_verdict"]
        assert verdict.sector_trend == "stable"
        assert verdict.district_saturation == "medium"

    def test_code_fenced_json_reply_is_tolerated(self, monkeypatch):
        monkeypatch.setattr(graph_module, "retrieve_market_chunks", lambda s, d: ROWS)
        monkeypatch.setattr(verdict_module, "complete", lambda *a, **k: f"```json\n{GOOD_REPLY}\n```")

        verdict = saudi_market_oracle_node(make_state())["market_verdict"]
        assert verdict.sector_trend == "growing"


class TestCitationHelpers:
    def test_prettify_maps_all_known_agencies(self):
        assert prettify_citation("Sama — X") == "SAMA — X"
        assert prettify_citation("Moc — X") == "MoC — X"
        assert prettify_citation("Monshaat — X") == "Monsha'at — X"
        assert prettify_citation("fsdp — X") == "FSDP — X"
        assert prettify_citation("hrsd — X") == "HRSD — X"
        assert prettify_citation("Simah — X") == "SIMAH — X"
        assert prettify_citation("Gastat — X") == "GASTAT — X"
        assert prettify_citation("Kafalah — X") == "Kafalah — X"

    def test_prettify_strips_invisible_characters(self):
        assert prettify_citation("Sama — Report\u2060") == "SAMA — Report"

    def test_build_sources_cited_skips_missing_citations(self):
        rows = [make_row("Sama — A", agency="Sama"), {"content": "x", "source_agency": "Moc", "citation": None, "score": 0.5}]
        assert build_sources_cited(rows) == ["SAMA — A"]

    def test_assemble_verdict_output_validates_against_model(self, monkeypatch):
        monkeypatch.setattr(verdict_module, "complete", lambda *a, **k: GOOD_REPLY)
        verdict = assemble_verdict(ROWS, sector="logistics", district="Al-Kharj")
        assert isinstance(verdict, MarketVerdict)
        assert MarketVerdict.model_validate(verdict.model_dump(mode="json")) == verdict
