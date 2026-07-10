"""
Offline ZATCA QR enrichment (architecture.md §1a, CONVENTIONS.md rule 4).

The THIRD, optional stage of document_intelligence_node, after extract ->
normalize. `normalize.py` deliberately passes `zatca_qr_base64` /
`zatca_verification_hash` through untouched; this module is the single place
that decodes the QR. It runs the Base64 TLV through core/zatca.py's
`ZatcaQRParser` **entirely offline** — there is no ZATCA API call — and, only
when the QR decodes as a well-formed Phase-2 TLV structure, populates
`zatca_verification_hash`.

What the hash is: `SHA256("<qr_base64>|<document_id>")`, mirroring
data/generate_synthetic_data.py::synthetic_hash(qr_base64, doc_id) — the
project's canonical convention. This is deliberately NOT the TLV tag-6 invoice
hash: Phase-2 *simplified* invoices (what the synthetic data and most SME
receipts carry) only populate tags 1-5, so tag 6 is usually absent. Hashing the
whole decoded QR payload gives a deterministic verification fingerprint for
every valid receipt, and matches the ground-truth hash so downstream code and
tests agree. Confirmed against core/zatca.py's tag map, which follows ZATCA's
published Phase-2 tag order (1 seller, 2 VAT no., 3 timestamp, 4 total, 5 VAT).

Failure contract (matches normalize.py): never crash the batch. A QR that is
present but does NOT decode as valid TLV leaves `zatca_verification_hash` None
and lowers `confidence_score` so the document surfaces as a flag for manual
review, rather than silently coercing a bad structure into a "verified" hash
(requirement: reject/flag rather than coerce). A document with no QR is
returned unchanged (hash stays None).
"""
from __future__ import annotations

import hashlib
import logging

from core.zatca import ZatcaParseError, ZatcaQRParser
from models import DocumentJSON

logger = logging.getLogger(__name__)

# A QR that is present but structurally undecodable is a genuine flag: the
# vision model saw something it read as a ZATCA QR, but it isn't valid TLV.
# Multiplicative penalty (same style as normalize.py) so it compounds with any
# extraction penalties already baked into confidence_score.
_PENALTY_QR_UNDECODABLE = 0.85


def _verification_hash(qr_base64: str, document_id: str) -> str:
    """Deterministic offline verification hash for a decoded QR.

    Mirrors data/generate_synthetic_data.py::synthetic_hash(qr_base64, doc_id)
    exactly (SHA256 of "<qr>|<doc_id>") so the value this node computes equals
    the ground-truth hash the synthetic generator wrote for the same receipt.
    """
    return hashlib.sha256(f"{qr_base64}|{document_id}".encode("utf-8")).hexdigest()


def enrich_with_zatca(doc: DocumentJSON) -> DocumentJSON:
    """Populates `zatca_verification_hash` from the document's ZATCA QR, offline.

    Returns a (possibly new) DocumentJSON:
      * no `zatca_qr_base64`              -> returned unchanged (hash stays None)
      * QR decodes as valid Phase-2 TLV  -> copy with `zatca_verification_hash` set
      * QR present but not valid TLV      -> copy with `confidence_score` lowered,
                                            hash left None (flagged, not coerced)

    Never raises: any parse failure is logged and turned into the flagged case.
    """
    qr_base64 = doc.zatca_qr_base64
    if not qr_base64 or not qr_base64.strip():
        return doc  # no QR present -> nothing to verify; hash remains None

    try:
        ZatcaQRParser(qr_base64).parse()
    except ZatcaParseError as exc:
        logger.warning(
            "zatca_enrich: QR present but not valid TLV for document_id=%s: %s "
            "— flagging (lowering confidence), leaving hash None",
            doc.document_id, exc,
        )
        return doc.model_copy(update={
            "confidence_score": round(doc.confidence_score * _PENALTY_QR_UNDECODABLE, 4),
        })

    return doc.model_copy(update={
        "zatca_verification_hash": _verification_hash(qr_base64, doc.document_id),
    })


__all__ = ["enrich_with_zatca"]
