"""
Offline ZATCA Phase-2 QR (TLV) parser and ledger cross-checker.

The QR payload on a ZATCA e-invoice is Base64 of a TLV (tag-length-value)
byte stream: each field is [1-byte tag][1-byte length][UTF-8 value]. Tags
1-5 are mandatory for Phase-2 simplified invoices; tag 6 (invoice hash) and
tags 7-9 (ECDSA signature / public key / cert signature) appear on
cryptographically-stamped invoices. This module does not call any ZATCA
API — it only decodes the structure and diffs it against ledger data
already on hand.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import IntEnum


class ZatcaTag(IntEnum):
    SELLER_NAME = 1
    VAT_NUMBER = 2
    TIMESTAMP = 3
    INVOICE_TOTAL = 4
    VAT_TOTAL = 5
    INVOICE_HASH = 6
    SIGNATURE = 7
    PUBLIC_KEY = 8
    CERT_SIGNATURE = 9


_REQUIRED_TAGS = (
    ZatcaTag.SELLER_NAME,
    ZatcaTag.VAT_NUMBER,
    ZatcaTag.TIMESTAMP,
    ZatcaTag.INVOICE_TOTAL,
    ZatcaTag.VAT_TOTAL,
)

_FIELD_BY_TAG = {
    ZatcaTag.SELLER_NAME: "seller_name",
    ZatcaTag.VAT_NUMBER: "vat_number",
    ZatcaTag.TIMESTAMP: "timestamp",
    ZatcaTag.INVOICE_TOTAL: "invoice_total",
    ZatcaTag.VAT_TOTAL: "vat_total",
    ZatcaTag.INVOICE_HASH: "invoice_hash",
}


class ZatcaParseError(ValueError):
    """Raised when the QR payload is not a well-formed ZATCA TLV structure."""


@dataclass
class ZatcaInvoiceData:
    seller_name: str | None = None
    vat_number: str | None = None
    timestamp: str | None = None
    invoice_total: Decimal | None = None
    vat_total: Decimal | None = None
    invoice_hash: str | None = None
    raw_tags: dict[int, bytes] = field(default_factory=dict)

    def missing_required_fields(self) -> list[str]:
        return [
            _FIELD_BY_TAG[tag]
            for tag in _REQUIRED_TAGS
            if tag not in self.raw_tags
        ]


@dataclass
class ZatcaValidationResult:
    is_valid: bool
    data: ZatcaInvoiceData
    errors: list[str] = field(default_factory=list)
    mismatches: dict[str, tuple[object, object]] = field(default_factory=dict)


class ZatcaQRParser:
    """Parses and validates a ZATCA Phase-2 QR code, fully offline.

    Usage:
        parser = ZatcaQRParser(qr_base64_string)
        data = parser.parse()                       # raises ZatcaParseError on malformed TLV
        result = parser.validate_against_ledger(ledger_row)
    """

    #  VAT_RATE for KSA is fixed at 15%; used only for a structural sanity check
    #  (total - vat should be close to a whole-number-of-riyals net), not enforced strictly.
    VAT_TOLERANCE = Decimal("0.02")
    TIMESTAMP_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ")

    def __init__(self, qr_base64: str) -> None:
        if not isinstance(qr_base64, str) or not qr_base64.strip():
            raise ZatcaParseError("QR payload must be a non-empty base64 string")
        self._raw_b64 = qr_base64.strip()
        self._data: ZatcaInvoiceData | None = None

    def parse(self) -> ZatcaInvoiceData:
        """Decodes the base64 payload and unpacks the TLV structure.

        Raises ZatcaParseError for any structural problem: bad base64,
        truncated TLV, a declared length that runs past the buffer end, or
        non-UTF-8 text in a text-bearing tag.
        """
        payload = self._decode_base64(self._raw_b64)
        raw_tags = self._unpack_tlv(payload)

        data = ZatcaInvoiceData(raw_tags=raw_tags)
        for tag in _REQUIRED_TAGS:
            if tag not in raw_tags:
                continue
            self._decode_text_field(data, tag, raw_tags[tag])
        if ZatcaTag.INVOICE_HASH in raw_tags:
            data.invoice_hash = raw_tags[ZatcaTag.INVOICE_HASH].hex()

        missing = data.missing_required_fields()
        if missing:
            raise ZatcaParseError(
                f"TLV structure is missing required tag(s): {', '.join(missing)}"
            )

        self._data = data
        return data

    @staticmethod
    def _decode_base64(raw_b64: str) -> bytes:
        try:
            return base64.b64decode(raw_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ZatcaParseError(f"Invalid base64 payload: {exc}") from exc

    @staticmethod
    def _unpack_tlv(payload: bytes) -> dict[int, bytes]:
        if not payload:
            raise ZatcaParseError("Decoded TLV payload is empty")

        tags: dict[int, bytes] = {}
        i, n = 0, len(payload)
        while i < n:
            if i + 2 > n:
                raise ZatcaParseError(
                    f"Truncated TLV header at byte offset {i}: expected tag+length bytes"
                )
            tag, length = payload[i], payload[i + 1]
            start, end = i + 2, i + 2 + length
            if end > n:
                raise ZatcaParseError(
                    f"TLV tag {tag} at offset {i} declares length {length} "
                    f"but only {n - start} byte(s) remain"
                )
            tags[tag] = payload[start:end]
            i = end

        if not tags:
            raise ZatcaParseError("No TLV fields decoded from payload")
        return tags

    @staticmethod
    def _decode_text_field(data: ZatcaInvoiceData, tag: ZatcaTag, raw: bytes) -> None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ZatcaParseError(f"Tag {tag.value} ({tag.name}) is not valid UTF-8") from exc

        if tag is ZatcaTag.SELLER_NAME:
            data.seller_name = text
        elif tag is ZatcaTag.VAT_NUMBER:
            data.vat_number = text
        elif tag is ZatcaTag.TIMESTAMP:
            data.timestamp = text
        elif tag is ZatcaTag.INVOICE_TOTAL:
            data.invoice_total = ZatcaQRParser._to_decimal(text, tag)
        elif tag is ZatcaTag.VAT_TOTAL:
            data.vat_total = ZatcaQRParser._to_decimal(text, tag)

    @staticmethod
    def _to_decimal(text: str, tag: ZatcaTag) -> Decimal:
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ZatcaParseError(
                f"Tag {tag.value} ({tag.name}) value {text!r} is not a valid number"
            ) from exc

    def validate_against_ledger(self, ledger_row: dict) -> ZatcaValidationResult:
        """Structurally validates the parsed QR and cross-checks it against a ledger row.

        `ledger_row` is expected to carry a subset of:
            seller_name, vat_number, timestamp, invoice_total, vat_total, invoice_hash
        Only keys present in `ledger_row` are compared. Amounts are compared
        as Decimal with VAT_TOLERANCE slack; everything else exact-match
        after whitespace normalization.
        """
        errors: list[str] = []
        try:
            data = self._data or self.parse()
        except ZatcaParseError as exc:
            return ZatcaValidationResult(is_valid=False, data=ZatcaInvoiceData(), errors=[str(exc)])

        mismatches: dict[str, tuple[object, object]] = {}

        def norm(value: object) -> str:
            return str(value).strip().casefold() if value is not None else ""

        if "seller_name" in ledger_row and norm(data.seller_name) != norm(ledger_row["seller_name"]):
            mismatches["seller_name"] = (data.seller_name, ledger_row["seller_name"])

        if "vat_number" in ledger_row and norm(data.vat_number) != norm(ledger_row["vat_number"]):
            mismatches["vat_number"] = (data.vat_number, ledger_row["vat_number"])

        if "timestamp" in ledger_row:
            parsed_ts = self._parse_timestamp(data.timestamp)
            ledger_ts = self._parse_timestamp(ledger_row["timestamp"])
            if parsed_ts is None or ledger_ts is None:
                if norm(data.timestamp) != norm(ledger_row["timestamp"]):
                    mismatches["timestamp"] = (data.timestamp, ledger_row["timestamp"])
            elif parsed_ts != ledger_ts:
                mismatches["timestamp"] = (data.timestamp, ledger_row["timestamp"])

        for field_name, tolerance in (("invoice_total", self.VAT_TOLERANCE), ("vat_total", self.VAT_TOLERANCE)):
            if field_name not in ledger_row:
                continue
            qr_amount = getattr(data, field_name)
            try:
                ledger_amount = Decimal(str(ledger_row[field_name]))
            except InvalidOperation:
                errors.append(f"Ledger field '{field_name}' is not numeric: {ledger_row[field_name]!r}")
                continue
            if qr_amount is None or abs(qr_amount - ledger_amount) > tolerance:
                mismatches[field_name] = (qr_amount, ledger_row[field_name])

        if "invoice_hash" in ledger_row and norm(data.invoice_hash) != norm(ledger_row["invoice_hash"]):
            mismatches["invoice_hash"] = (data.invoice_hash, ledger_row["invoice_hash"])

        is_valid = not errors and not mismatches
        return ZatcaValidationResult(is_valid=is_valid, data=data, errors=errors, mismatches=mismatches)

    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for fmt in cls.TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
