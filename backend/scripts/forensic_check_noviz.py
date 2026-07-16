"""
THROWAWAY diagnostic — measures the forensic node's verdicts in ISOLATION from
vision/OCR, against the live-reseeded Rawad Logistics data. No vision calls, no
uploads, no OpenAI calls for extraction (forensic flag *descriptions* still call
GPT-5.4 Mini, same as production). Read-only against Supabase — writes nothing.

Loads the already-seeded extracted_documents for Rawad's application straight
from agent_results (the clean DocumentJSON rows data/generate_synthetic_data.py
wrote), runs the real reconcile_against_ledger + build_forensic_report against
the live mock_open_banking_ledger, and cross-references data/ground_truth.json
so each flag can be matched back to its manifest bucket (legit/fabricated/mismatch).

Run: cd backend && .venv/Scripts/python.exe scripts/forensic_check_noviz.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from core.supabase import get_service_client  # noqa: E402
from models import DocumentJSON  # noqa: E402
from nodes.forensic.matching import reconcile_against_ledger  # noqa: E402
from nodes.forensic.scoring import build_forensic_report  # noqa: E402

RAWAD_COMPANY = "Rawad Logistics"


def main() -> None:
    manifest = json.loads((REPO_ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))
    rawad = next(s for s in manifest["smes"] if s["company_name"] == RAWAD_COMPANY)
    application_id = rawad["application_id"]
    cr_number = rawad["cr_number"]
    bucket_by_doc_id = {d["document_id"]: d for d in rawad["documents"]}

    svc = get_service_client()
    raw_docs = svc.table("agent_results").select("extracted_documents").eq(
        "application_id", application_id
    ).limit(1).execute().data[0]["extracted_documents"]
    documents = [DocumentJSON.model_validate(d) for d in raw_docs]
    doc_by_id = {d.document_id: d for d in documents}

    print(f"application_id: {application_id}")
    print(f"cr_number: {cr_number}")
    print(f"documents loaded from agent_results.extracted_documents: {len(documents)}\n")

    # No `describe` callback -> build_forensic_report uses the deterministic
    # default_flag_description template (no OpenAI call), per instructions to
    # not call OpenAI at all in this diagnostic. Production's
    # forensic_accountant_node normally passes write_flag_descriptions
    # (GPT-5.4 Mini) here instead.
    matches, invoice_context = reconcile_against_ledger(cr_number, documents)
    report = build_forensic_report(matches)

    print(f"overall_status: {report.overall_status}")
    print(f"reconciliation_rate: {report.reconciliation_rate:.4f}")
    print(f"discrepancy_flags: {len(report.discrepancy_flags)}\n")

    # Map each flag description back to the document it's about, via the
    # document_id substring explain.py/scoring.py's templates always include.
    flagged_doc_ids: set[str] = set()
    for flag in report.discrepancy_flags:
        matched_id = next((doc_id for doc_id in doc_by_id if doc_id in flag.description), None)
        flagged_doc_ids.add(matched_id) if matched_id else None
        gt_entry = bucket_by_doc_id.get(matched_id) if matched_id else None
        doc = doc_by_id.get(matched_id) if matched_id else None
        bucket = gt_entry["bucket"] if gt_entry else "UNKNOWN"
        expected = gt_entry["expected_flag"] if gt_entry else "UNKNOWN"
        vendor = doc.vendor if doc else "?"
        print(f"[{flag.severity}] bucket={bucket} expected={expected} vendor={vendor} doc_id={matched_id}")
        print(f"    {flag.description}\n")

    print("=" * 80)
    print("Cross-reference: every document vs. its manifest bucket and outcome")
    print("=" * 80)
    unexpected_legit_flags = []
    for gt_entry in rawad["documents"]:
        doc_id = gt_entry["document_id"]
        bucket = gt_entry["bucket"]
        expected = gt_entry["expected_flag"]
        doc = doc_by_id.get(doc_id)
        got_flag = doc_id in flagged_doc_ids
        vendor = doc.vendor if doc else "MISSING FROM extracted_documents"
        status = "FLAGGED" if got_flag else "clean (no flag)"
        print(f"bucket={bucket:10s} expected={expected:6s} vendor={vendor or '?':22s} doc_id={doc_id} -> {status}")
        if bucket == "legit" and got_flag:
            unexpected_legit_flags.append(doc_id)

    print()
    if unexpected_legit_flags:
        print(f"LEGIT docs that got a flag (should be clean/green): {len(unexpected_legit_flags)}")
        for doc_id in unexpected_legit_flags:
            print(f"  {doc_id}")
    else:
        print("No legit doc got a flag.")

    fabricated_ids = [d["document_id"] for d in rawad["documents"] if d["bucket"] == "fabricated"]
    print(f"\nFabricated doc(s): {fabricated_ids}")
    for fid in fabricated_ids:
        doc = doc_by_id.get(fid)
        print(f"  vendor={doc.vendor if doc else '?'} amount={doc.extracted_amount if doc else '?'}")
        for flag in report.discrepancy_flags:
            if fid in flag.description:
                print(f"  -> [{flag.severity}] {flag.description}")


if __name__ == "__main__":
    main()
