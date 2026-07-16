"""
Saudi Market Oracle — verdict assembly (architecture.md §1, schema_mapping.md Node 4).

One GPT-5.4 Mini call via core.llm.complete, grounded STRICTLY in the chunk
text retrieved by retrieve.py. The model returns JSON with sector_trend /
district_saturation / oracle_insight only; sources_cited is built
DETERMINISTICALLY in Python from the retrieved rows' citation values — the
LLM never invents citations (mirrors how forensic scoring keeps severity out
of the model's hands).

Fallback contract (like nodes/forensic/explain.py and devils_advocate/
narrate.py): empty retrieval, LLMError, or an unparseable/invalid reply all
yield a deterministic honest MarketVerdict — the graph never crashes here.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.llm import LLMError, complete
from models import MarketVerdict
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Raw folder-derived agency names as stored by the ingest -> display form.
AGENCY_DISPLAY = {
    "Sama": "SAMA",
    "Moc": "MoC",
    "Monshaat": "Monsha'at",
    "fsdp": "FSDP",
    "hrsd": "HRSD",
    "Simah": "SIMAH",
    "Gastat": "GASTAT",
    "Kafalah": "Kafalah",
}

# Ingested citations can carry invisible word-joiner/bidi characters copied
# out of the PDFs; strip them so displayed citations are clean.
_INVISIBLE_CHARS = re.compile("[\u2060\u200b\u200e\u200f\ufeff]")


def prettify_citation(citation: str) -> str:
    """Maps raw folder-name agency tokens to display form inside a citation
    string and strips invisible characters. Deterministic, no LLM."""
    text = _INVISIBLE_CHARS.sub("", citation).strip()
    for raw, display in AGENCY_DISPLAY.items():
        text = re.sub(rf"\b{re.escape(raw)}\b", display, text)
    return text


def build_sources_cited(rows: list[dict[str, Any]]) -> list[str]:
    """Deduped, order-preserved, prettified citations from retrieved rows."""
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        raw = row.get("citation")
        if not raw:
            continue
        pretty = prettify_citation(str(raw))
        if pretty and pretty not in seen:
            seen.add(pretty)
            out.append(pretty)
    return out


def _fallback_verdict(rows: list[dict[str, Any]], sector: str | None, district: str | None) -> MarketVerdict:
    """Deterministic honest verdict when retrieval or the model fails."""
    return MarketVerdict(
        sector_trend="stable",
        district_saturation="medium",
        oracle_insight=(
            f"There is insufficient grounded market data in the retrieved regulator "
            f"reports to assess the {sector or 'stated'} sector in "
            f"{district or 'the stated district'}; defaulting to a neutral view."
        ),
        sources_cited=build_sources_cited(rows),
    )


_SYSTEM_PROMPT = (
    "You are a market analyst for a Saudi bank assessing an SME loan applicant. "
    "You are given excerpts retrieved from official Saudi regulator and agency "
    "reports (the excerpts may be in Arabic — read them as-is, do not translate). "
    "Ground your assessment STRICTLY in the provided excerpts; if they do not "
    "support a conclusion, choose the neutral option. Reply with JSON ONLY."
)


def _build_prompt(rows: list[dict[str, Any]], sector: str | None, district: str | None) -> str:
    excerpts = "\n\n".join(
        f"[Source {i + 1}: {prettify_citation(str(r.get('citation') or r.get('source_agency') or 'unknown'))}]\n"
        f"{r['content']}"
        for i, r in enumerate(rows)
    )
    return (
        f"SME under review — sector: {sector or 'unknown'}; district: {district or 'unknown'}.\n\n"
        f"Retrieved report excerpts:\n{excerpts}\n\n"
        "Based ONLY on these excerpts, return a JSON object with exactly these keys:\n"
        '  "sector_trend": one of "growing" | "stable" | "declining"\n'
        '  "district_saturation": one of "low" | "medium" | "high"\n'
        '  "oracle_insight": 2-3 sentences in English naming the sources '
        "(e.g. SAMA, Monsha'at) that support your assessment.\n"
        "No other keys. JSON only."
    )


def assemble_verdict(
    rows: list[dict[str, Any]],
    *,
    sector: str | None,
    district: str | None,
) -> MarketVerdict:
    """Grounded MarketVerdict from retrieved rows; falls back deterministically."""
    if not rows:
        return _fallback_verdict(rows, sector, district)

    try:
        reply = complete(
            _build_prompt(rows, sector, district),
            system=_SYSTEM_PROMPT,
            max_tokens=400,
        )
    except LLMError as exc:
        logger.warning("oracle: LLM call failed, using fallback verdict: %s", exc)
        return _fallback_verdict(rows, sector, district)

    try:
        # Tolerate code fences the mini model sometimes adds around JSON.
        cleaned = re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return MarketVerdict(
            sector_trend=data["sector_trend"],
            district_saturation=data["district_saturation"],
            oracle_insight=str(data["oracle_insight"]).strip(),
            # Citations are NEVER taken from the model — deterministic only.
            sources_cited=build_sources_cited(rows),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
        logger.warning("oracle: unparseable/invalid LLM reply, using fallback: %s", exc)
        return _fallback_verdict(rows, sector, district)


__all__ = [
    "AGENCY_DISPLAY",
    "prettify_citation",
    "build_sources_cited",
    "assemble_verdict",
]
