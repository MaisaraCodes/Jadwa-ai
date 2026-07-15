"""
Raw vision-LLM output -> DocumentJSON normalization (architecture.md §1, Node 1).

`document_intelligence_node` runs a GPT-5.4 vision pass over each uploaded file
and gets back a loosely-shaped dict: Arabic, English, or a mix of both on the
same document, PDF / photo / scan, ZATCA receipt or plain invoice, well-formed
or messy. This module is the single place that turns any of those into a
canonical `DocumentJSON` (models.py — the SINGLE SOURCE OF TRUTH; we import
that shape, never redefine it — CONVENTIONS.md rule 7). There is deliberately
no per-language branch anywhere here: every input goes through the same digit/
currency/date/type coercion regardless of source language, and vendor/
line_item text is stripped of invisible bidi control characters (never
transliterated) so mixed-script strings survive storage and display intact.

Design contract:
  * Never crash on messy input. A half-extracted document must still yield a
    valid (lower-confidence) DocumentJSON so it doesn't block the whole batch;
    only a document that can't be coerced into the schema at all returns None
    for the caller to flag for manual review.
  * Pydantic is the final gate: we build a plain dict and hand it to
    `DocumentJSON.model_validate(...)`. If that still fails, we log the raw
    input and return None rather than raising.
  * confidence_score is adjusted DOWN (not passed through) whenever a field had
    to be defaulted, guessed, or recovered from a fallback parse.

Out of scope (separate tasks — do not touch here): the extraction prompt, the
forensic matching logic, and the ZATCA QR/TLV parser (core/zatca.py). We only
pass `zatca_qr_base64` / `zatca_verification_hash` through untouched.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser
from pydantic import ValidationError

from models import DocumentJSON, DocumentType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Digit normalization
# ---------------------------------------------------------------------------
# Arabic-Indic (U+0660-U+0669) and Extended/Persian (U+06F0-U+06F9) digits both
# show up on Saudi receipts depending on the font/keyboard. Map both to ASCII
# BEFORE any numeric or date parsing so downstream code only ever sees 0-9.
_DIGIT_TRANSLATION = {
    **{0x0660 + i: str(i) for i in range(10)},  # ٠-٩
    **{0x06F0 + i: str(i) for i in range(10)},  # ۰-۹
    0x066B: ".",  # ٫ Arabic decimal separator -> "."
    0x066C: ",",  # ٬ Arabic thousands separator -> ","
}


def _to_western_digits(text: str) -> str:
    """Converts Arabic-Indic / Persian digits (and their separators) to ASCII."""
    return text.translate(_DIGIT_TRANSLATION)


# ---------------------------------------------------------------------------
# Bidi/directionality control-character stripping
# ---------------------------------------------------------------------------
# RTL text copied out of PDFs/OCR frequently carries invisible bidi control
# characters (embedding/override/isolate marks) around Latin substrings, e.g. a
# brand name embedded in an Arabic receipt. These are invisible in a rendered
# PDF but corrupt downstream storage/display (mismatched paired marks, reversed
# rendering in contexts that don't run the bidi algorithm, broken string
# comparisons/search). Strip them; never touch the script itself (no
# transliteration) and never touch ZWJ/ZWNJ (U+200C/200D), which are real
# Arabic/Persian letter-shaping characters, not artifacts.
_BIDI_CONTROL_CHARS = re.compile(
    "[‎‏‪-‮⁦-⁩﻿]"
)


def _strip_bidi_controls(text: str) -> str:
    """Removes bidi/directionality control chars and BOM; preserves the script."""
    return _BIDI_CONTROL_CHARS.sub("", text)


# ---------------------------------------------------------------------------
# Field-alias lookup — the vision LLM is not guaranteed to use our exact keys.
# ---------------------------------------------------------------------------
_AMOUNT_KEYS = ("extracted_amount", "amount", "total", "invoice_total", "grand_total", "total_amount")
_DATE_KEYS = ("date", "invoice_date", "issue_date", "transaction_date", "issued_at")
_VENDOR_KEYS = ("vendor", "seller", "seller_name", "supplier", "merchant", "store_name")
_TYPE_KEYS = ("type", "document_type", "doc_type", "category")
_CURRENCY_KEYS = ("currency", "currency_code")
_LINE_ITEM_KEYS = ("line_items", "items", "lines", "products")
_CONFIDENCE_KEYS = ("confidence_score", "confidence", "score")
_ZATCA_HASH_KEYS = ("zatca_verification_hash", "zatca_hash", "verification_hash", "invoice_hash")
_ZATCA_QR_KEYS = ("zatca_qr_base64", "zatca_qr", "qr_base64", "qr_code", "qr")


def _first_present(raw: dict, keys: tuple[str, ...]) -> Any:
    """Returns the first non-empty value among `keys`, else None."""
    for key in keys:
        if key in raw:
            value = raw[key]
            if value is not None and not (isinstance(value, str) and not value.strip()):
                return value
    return None


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------
# Currency words/symbols we strip out of an amount string. Order the multi-char
# tokens are removed doesn't matter — we blank each one wherever it appears.
_CURRENCY_TOKENS = (
    "sar", "sr", "ريال", "ر.س", "ر.س.", "﷼", "usd", "us$", "$", "eur", "€", "aed", "درهم",
)
_AMOUNT_CHARS = re.compile(r"[^0-9.\-]")  # everything that isn't a digit / dot / minus
_FIRST_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_amount(raw_amount: Any) -> tuple[float | None, bool]:
    """Parses an amount to float.

    Returns (value, recovered):
      * (float, False)  — parsed cleanly from a well-formed number/string
      * (float, True)   — value only recoverable via a fallback regex extract
      * (None,  False)  — nothing numeric found; caller defaults + penalizes hard
    Never raises.
    """
    if raw_amount is None:
        return None, False
    if isinstance(raw_amount, bool):  # guard: bool is an int subclass
        return None, False
    if isinstance(raw_amount, (int, float)):
        return float(raw_amount), False

    text = _to_western_digits(str(raw_amount)).strip().lower()
    for token in _CURRENCY_TOKENS:
        text = text.replace(token, " ")
    # Drop thousands separators, then any remaining stray characters.
    cleaned = _AMOUNT_CHARS.sub("", text.replace(",", ""))

    if cleaned and cleaned not in ("-", ".", "-."):
        try:
            return float(cleaned), False
        except ValueError:
            pass

    # Fallback: pull the first number-looking token out of the messy string.
    match = _FIRST_NUMBER.search(text.replace(",", ""))
    if match:
        try:
            return float(match.group()), True
        except ValueError:
            return None, False
    return None, False


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
def _parse_date(raw_date: Any) -> date | None:
    """Parses many date formats into a `date`. Never raises; None on failure.

    Handles DD/MM/YYYY, YYYY-MM-DD, "12 Oct 2025", and Arabic-digit variants
    (digits are westernized first). dayfirst=True because DD/MM/YYYY is the
    Saudi convention — "05/10/2025" is 5 October, not 10 May.
    """
    if isinstance(raw_date, datetime):
        return raw_date.date()
    if isinstance(raw_date, date):
        return raw_date
    if raw_date is None:
        return None

    text = _to_western_digits(str(raw_date)).strip()
    if not text:
        return None
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Currency detection
# ---------------------------------------------------------------------------
# Explicit non-SAR mentions we recognize -> ISO code. SAR is the DocumentJSON
# default and is used whenever nothing else is clearly indicated.
_CURRENCY_MAP = {
    "usd": "USD", "us$": "USD", "$": "USD", "dollar": "USD",
    "eur": "EUR", "€": "EUR", "euro": "EUR",
    "aed": "AED", "درهم": "AED", "dirham": "AED",
    "gbp": "GBP", "£": "GBP",
}
_SAR_HINTS = ("sar", "sr", "ريال", "ر.س", "﷼", "riyal")


def _normalize_currency(currency_field: Any, amount_raw: Any) -> str:
    """Normalizes currency to SAR unless another currency is explicitly present.

    Checks the dedicated currency field first, then any currency word/symbol
    embedded in the raw amount string. Defaults to "SAR" (DocumentJSON default).
    """
    for source in (currency_field, amount_raw):
        if source is None:
            continue
        text = _to_western_digits(str(source)).strip().lower()
        if not text:
            continue
        for token, code in _CURRENCY_MAP.items():
            if token in text:
                return code
        if any(hint in text for hint in _SAR_HINTS):
            return "SAR"
    return "SAR"


# ---------------------------------------------------------------------------
# Document type mapping
# ---------------------------------------------------------------------------
# Free-text type description -> DocumentType literal. Checked in order, so more
# specific patterns (zatca receipt) must precede generic ones (invoice). Arabic
# synonyms included: فاتورة=invoice, كشف حساب=bank statement, عقد=contract,
# إيصال/سند=receipt.
_TYPE_PATTERNS: tuple[tuple[DocumentType, tuple[str, ...]], ...] = (
    ("zatca_receipt", ("zatca", "fatoora", "e-invoice", "einvoice", "tax invoice", "vat invoice", "إيصال", "سند", "فاتورة ضريبية")),
    ("bank_statement", ("bank statement", "statement", "account statement", "كشف حساب", "كشف الحساب")),
    ("contract", ("contract", "agreement", "عقد", "اتفاقية")),
    ("invoice", ("invoice", "bill", "receipt", "فاتورة")),
)
_VALID_TYPES = frozenset(("zatca_receipt", "invoice", "bank_statement", "contract", "other"))


def _normalize_type(raw_type: Any) -> tuple[DocumentType, bool]:
    """Maps a free-text type to a DocumentType literal.

    Returns (type, unrecognized): unrecognized=True when a type description was
    present but couldn't be classified (so we defaulted to "other" and should
    lower confidence) — distinct from no type field being provided at all.
    """
    if raw_type is None:
        return "other", False

    text = _to_western_digits(str(raw_type)).strip().lower()
    if not text:
        return "other", False

    # An exact literal from the LLM is trusted as-is.
    if text in _VALID_TYPES:
        return text, False  # type: ignore[return-value]

    for doc_type, needles in _TYPE_PATTERNS:
        if any(needle in text for needle in needles):
            return doc_type, False
    return "other", True


# ---------------------------------------------------------------------------
# Line items
# ---------------------------------------------------------------------------
def _normalize_line_items(raw_items: Any) -> list[str]:
    """Coerces line items into list[str]. Accepts a list of strings or of
    dicts (using a description/name field), or a single string. Never raises.
    """
    if raw_items is None:
        return []
    if isinstance(raw_items, str):
        stripped = raw_items.strip()
        return [stripped] if stripped else []
    if not isinstance(raw_items, (list, tuple)):
        return []

    items: list[str] = []
    for entry in raw_items:
        if entry is None:
            continue
        if isinstance(entry, str):
            text = entry.strip()
        elif isinstance(entry, dict):
            label = entry.get("description") or entry.get("name") or entry.get("item") or entry.get("label")
            text = str(label).strip() if label is not None else ""
        else:
            text = str(entry).strip()
        text = _strip_bidi_controls(text).strip()
        if text:
            items.append(text)
    return items


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------
# Multiplicative penalties applied to the LLM's stated confidence for each
# field we had to default, guess, or recover. Multiplicative so several small
# gaps compound instead of a single field zeroing the score.
_DEFAULT_CONFIDENCE = 0.6       # used when the LLM gave no confidence at all
_PENALTY_AMOUNT_MISSING = 0.35  # no amount at all -> defaulted to 0.0 (severe)
_PENALTY_AMOUNT_RECOVERED = 0.8  # amount only found via fallback regex
_PENALTY_DATE_MISSING = 0.35    # unparseable date -> defaulted to today (severe)
_PENALTY_TYPE_UNRECOGNIZED = 0.9
_PENALTY_VENDOR_MISSING = 0.9
_PENALTY_NO_CONFIDENCE = 0.9    # LLM didn't report confidence -> mild discount


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _base_confidence(raw_confidence: Any) -> tuple[float, bool]:
    """Returns (base, was_missing). Coerces the LLM's confidence into [0,1];
    falls back to _DEFAULT_CONFIDENCE if absent or unparseable."""
    if raw_confidence is None:
        return _DEFAULT_CONFIDENCE, True
    try:
        return _clamp01(float(raw_confidence)), False
    except (TypeError, ValueError):
        return _DEFAULT_CONFIDENCE, True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def normalize_extracted_document(raw: dict, document_id: str) -> DocumentJSON | None:
    """Normalizes one raw vision-LLM extraction dict into a `DocumentJSON`.

    Robust to Arabic/English, PDF/photo/scan, ZATCA receipt/plain invoice, and
    well-formed/messy input. Missing or unparseable fields fall back to safe
    defaults (vendor=None, line_items=[], amount=0.0, date=today) and lower the
    confidence_score instead of raising.

    The signature in the task reads `-> DocumentJSON`; it is `DocumentJSON |
    None` in practice because requirement 9 makes Pydantic the final gate: if
    validation still fails after normalization we log the raw input and return
    None so the caller can flag the document for manual review rather than
    crash the whole document_intelligence_node run.
    """
    if not isinstance(raw, dict):
        logger.error("normalize: expected dict, got %s for document_id=%s", type(raw).__name__, document_id)
        return None

    base_conf, conf_missing = _base_confidence(_first_present(raw, _CONFIDENCE_KEYS))
    confidence = base_conf
    if conf_missing:
        confidence *= _PENALTY_NO_CONFIDENCE

    # --- amount ---
    amount_raw = _first_present(raw, _AMOUNT_KEYS)
    amount, recovered = _parse_amount(amount_raw)
    if amount is None:
        amount = 0.0
        confidence *= _PENALTY_AMOUNT_MISSING
    elif recovered:
        confidence *= _PENALTY_AMOUNT_RECOVERED

    # --- date ---
    parsed_date = _parse_date(_first_present(raw, _DATE_KEYS))
    if parsed_date is None:
        parsed_date = date.today()
        confidence *= _PENALTY_DATE_MISSING

    # --- type ---
    doc_type, type_unrecognized = _normalize_type(_first_present(raw, _TYPE_KEYS))
    if type_unrecognized:
        confidence *= _PENALTY_TYPE_UNRECOGNIZED

    # --- vendor ---
    # Preserve the original script verbatim (no transliteration) but strip
    # invisible bidi/directionality control characters, which break storage,
    # search, and display without being visible in the source document.
    vendor_raw = _first_present(raw, _VENDOR_KEYS)
    vendor = _strip_bidi_controls(str(vendor_raw)).strip() if vendor_raw is not None else None
    if not vendor:
        vendor = None
        confidence *= _PENALTY_VENDOR_MISSING

    # --- currency / line items / ZATCA passthrough ---
    currency = _normalize_currency(_first_present(raw, _CURRENCY_KEYS), amount_raw)
    line_items = _normalize_line_items(_first_present(raw, _LINE_ITEM_KEYS))

    zatca_hash = _first_present(raw, _ZATCA_HASH_KEYS)
    zatca_qr = _first_present(raw, _ZATCA_QR_KEYS)

    payload = {
        "document_id": document_id,
        "type": doc_type,
        "vendor": vendor,
        "extracted_amount": amount,
        "currency": currency,
        "date": parsed_date,
        "line_items": line_items,
        "zatca_verification_hash": str(zatca_hash) if zatca_hash is not None else None,
        "zatca_qr_base64": str(zatca_qr) if zatca_qr is not None else None,
        "confidence_score": round(_clamp01(confidence), 4),
    }

    try:
        return DocumentJSON.model_validate(payload)
    except ValidationError as exc:
        logger.error(
            "normalize: DocumentJSON validation failed for document_id=%s; raw=%r; errors=%s",
            document_id, raw, exc.errors(),
        )
        return None


__all__ = ["normalize_extracted_document"]
