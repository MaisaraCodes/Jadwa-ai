"""
Vision extraction: uploaded file -> raw fields dict (architecture.md §1, Node 1).

This is the FIRST half of document_intelligence_node — the GPT-5.4 vision pass
that reads a receipt/invoice/statement image and returns a loosely-shaped dict.
The SECOND half (document_intelligence/normalize.py) coerces that dict into a
canonical DocumentJSON. Keeping them separate is deliberate: extraction is the
only part that touches the model, so it's the only part that can fail on a bad
key / rate limit / malformed reply — and when it does, we return {} and let
normalize produce a valid, very-low-confidence DocumentJSON rather than block
the whole batch.

The prompt is in English (CONVENTIONS.md: Arabic is token-heavy) but the
documents themselves are frequently Arabic, English, or a mix of both on the
same page (e.g. an Arabic ZATCA receipt with an English brand name) — the
model is told to keep original text verbatim in whichever script(s) it's
printed, and to transcribe digits/dates as-shown rather than convert them, so
normalize (document_intelligence/normalize.py) is the single place that
westernizes digits, parses dates/amounts, and maps types, regardless of
source language. There is no per-language branch anywhere in this pipeline.
"""
from __future__ import annotations

import json
import logging
import re

from core.llm import LLMError, complete_vision
from models import UploadedFile

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a document extraction engine for a Saudi SME lending platform. "
    "You are shown a single business document — a ZATCA tax receipt, an "
    "invoice, a bank statement, or a contract — which may be in Arabic, "
    "English, or a mix of both on the same document (e.g. an Arabic receipt "
    "with an English brand name, or Arabic line items with English part "
    "numbers) and may be a photo, scan, or PDF page. Extract the fields you "
    "can see and reply with a SINGLE JSON object and nothing else. Never "
    "invent values: if a field is not visible, use null (or [] for "
    "line_items). Keep original text verbatim for names and line items in "
    "whichever script(s) they are printed; do not translate or transliterate. "
    "Always report amounts as a plain number and dates in the format printed "
    "— a downstream step normalizes digits, separators, and date formats, so "
    "just transcribe exactly what you see rather than converting it yourself."
)

# The JSON shape we ask for maps directly onto normalize's accepted keys. Every
# field is best-effort — normalize handles missing/messy values and adjusts
# confidence, so the model is told to report its OWN confidence honestly here.
_USER_PROMPT = (
    "Extract this document into a JSON object with exactly these keys:\n"
    '  "type": one of "zatca_receipt" | "invoice" | "bank_statement" | "contract" | "other"\n'
    '  "vendor": the seller/merchant/counterparty name, or null\n'
    '  "extracted_amount": the total amount as a number (digits only), or null\n'
    '  "currency": the currency shown (e.g. "SAR"), or null\n'
    '  "date": the document date exactly as printed (any format), or null\n'
    '  "line_items": array of short item description strings (may be empty)\n'
    '  "zatca_qr_base64": the raw Base64 text of the ZATCA QR code if one is '
    "printed and legible, else null\n"
    '  "confidence_score": your own confidence 0.0-1.0 that the reading is correct — '
    "score honestly for how hard THIS document actually was: a document with mixed "
    "Arabic/English text, a low-quality scan, glare, or handwriting is genuinely "
    "harder to read correctly than a clean single-language print, so it should get "
    "a lower score, not the same score as an easy document\n"
    "Reply with the JSON object only — no markdown fences, no commentary."
)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Tolerantly pulls a JSON object out of the model's reply.

    Tries a straight parse first, then falls back to the outermost {...} span
    (in case the model wrapped it in prose or ```json fences despite the
    instruction). Raises ValueError if nothing parseable is found.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT.search(text)
        if not match:
            raise ValueError("no JSON object found in model reply")
        parsed = json.loads(match.group())  # may raise JSONDecodeError -> ValueError below

    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def extract_document_fields(document: UploadedFile) -> dict:
    """Runs the vision model over one uploaded file and returns a raw fields dict.

    Never raises: on any model or parse failure it logs and returns {} — an
    empty dict is a valid input to normalize_extracted_document, which turns it
    into a valid (very-low-confidence) DocumentJSON so a single unreadable file
    can't sink the whole batch.
    """
    try:
        reply = complete_vision(_USER_PROMPT, document.storage_url, system=_SYSTEM_PROMPT, json_mode=True)
    except LLMError as exc:
        logger.warning("extract: vision call failed for document_id=%s: %s", document.document_id, exc)
        return {}

    try:
        return _extract_json(reply)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "extract: could not parse JSON for document_id=%s: %s; reply=%r",
            document.document_id, exc, reply,
        )
        return {}


__all__ = ["extract_document_fields"]
