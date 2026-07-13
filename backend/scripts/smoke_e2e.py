"""
Live end-to-end smoke test (Phase 2 acceptance run — SYNTHETIC_DATA_SPEC.md).

Drives the REAL flow against a live backend + Supabase + OpenAI: signs in as
the seeded Rawad Logistics SME, creates a fresh draft application, renders
Rawad's 20-document batch (ground_truth.json) as real receipt/invoice images
and uploads them, POST /process (real GPT-5.4 vision extraction, real
forensic Python matching against mock_open_banking_ledger, real GPT-5.4 Mini
flag descriptions), polls /status, reads GET /bank/applications/{id}, checks
the acceptance criteria, then deletes everything it created.

Starts its own uvicorn subprocess and shuts it down again — safe to rerun:
    cd backend && .venv/Scripts/python.exe scripts/smoke_e2e.py

Requires: backend/.env (OPENAI_API_KEY, SUPABASE_*, DATABASE_URL) and the
synthetic dataset already seeded (data/generate_synthetic_data.py --reset).
Never prints secret values.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

import os  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from core.supabase import get_anon_client, get_service_client  # noqa: E402

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("PORT", "8000")
BASE_URL = f"http://{HOST}:{PORT}/api/v1"
DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "Jadwa-Demo-2026!")

RAWAD_COMPANY = "Rawad Logistics"
RAWAD_EMAIL = "mohammed@rawad-logistics.sa.demo"
BANK_EMAIL = "khalid@alinma.sa.demo"

BUCKET = "application-documents"
DOCUMENTS_TABLE = "application_documents"
AGENT_RESULTS_TABLE = "agent_results"
APPLICATIONS_TABLE = "applications"

FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"

STATUS_POLL_INTERVAL_S = 3
STATUS_POLL_TIMEOUT_S = 600


class SmokeTestError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Receipt image rendering — real images for the real vision model to read.
# ---------------------------------------------------------------------------
def render_receipt_image(doc: dict) -> bytes:
    W, H = 900, 1150
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_BOLD, 34)
    label_font = ImageFont.truetype(FONT_REGULAR, 26)
    amount_font = ImageFont.truetype(FONT_BOLD, 30)  # bigger + bold: decimal points must survive OCR
    mono_font = ImageFont.truetype(FONT_MONO, 16)

    y = 40
    draw.text((40, y), doc["vendor"] or "Unknown Vendor", font=title_font, fill="black")
    y += 50
    kind = "ZATCA Tax Receipt" if doc["type"] == "zatca_receipt" else doc["type"].replace("_", " ").title()
    draw.text((40, y), kind, font=label_font, fill="black")
    y += 60
    draw.line((40, y, W - 40, y), fill="black", width=2)
    y += 30

    total = doc["extracted_amount"]
    vat = round(total - total / 1.15, 2)
    subtotal = round(total - vat, 2)

    lines = [
        f"Date: {doc['date']}",
        f"Currency: {doc['currency']}",
        "",
        "Line items:",
    ]
    lines += [f"  - {li}" for li in doc.get("line_items", [])]
    for line in lines:
        draw.text((40, y), line, font=label_font, fill="black")
        y += 34

    y += 10
    # Thousands separators + a larger bold font so the decimal point can't be
    # lost to OCR/anti-aliasing the way it was at 26px regular weight.
    for label, value in (("Subtotal", subtotal), ("VAT (15%)", vat), ("TOTAL", total)):
        draw.text((40, y), f"{label}: {value:,.2f} {doc['currency']}", font=amount_font, fill="black")
        y += 42

    if doc.get("zatca_qr_base64"):
        y += 30
        draw.line((40, y, W - 40, y), fill="black", width=2)
        y += 20
        draw.text((40, y), "ZATCA QR (Base64):", font=label_font, fill="black")
        y += 34
        for line in textwrap.wrap(doc["zatca_qr_base64"], width=48):
            draw.text((40, y), line, font=mono_font, fill="black")
            y += 22

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Uvicorn lifecycle
# ---------------------------------------------------------------------------
SERVER_LOG_PATH = BACKEND_DIR / "scripts" / "_smoke_e2e_server.log"


def start_server() -> tuple[subprocess.Popen, "io.TextIOWrapper"]:
    # Fail loudly instead of silently polling an already-running (possibly
    # stale, pre-fix) process on this port — bit us once already.
    try:
        httpx.get(f"http://{HOST}:{PORT}/health", timeout=1.0)
        raise SmokeTestError(
            f"Port {PORT} is already serving a response — an old server is still "
            f"running. Stop it before rerunning this script."
        )
    except httpx.HTTPError:
        pass  # good: nothing answering yet

    log_file = open(SERVER_LOG_PATH, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", HOST, "--port", str(PORT)],
        cwd=str(BACKEND_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            log_file.flush()
            raise SmokeTestError(f"uvicorn exited early — see {SERVER_LOG_PATH}")
        try:
            r = httpx.get(f"http://{HOST}:{PORT}/health", timeout=1.0)
            if r.status_code == 200:
                return proc, log_file
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise SmokeTestError("uvicorn did not become healthy within 30s")


def stop_server(proc: subprocess.Popen, log_file) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    log_file.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def sign_in(email: str) -> str:
    anon = get_anon_client()
    res = anon.auth.sign_in_with_password({"email": email, "password": DEMO_PASSWORD})
    if not res.session or not res.session.access_token:
        raise SmokeTestError(f"sign-in failed for {email}")
    return res.session.access_token


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def find_rawad_seed(svc) -> tuple[str, list[dict]]:
    """Returns (seeded_application_id, extracted_documents) for the ORIGINAL
    seeded Rawad application (data/generate_synthetic_data.py). We read its
    already-seeded documents as the source content to render into images —
    we do NOT touch or modify this seeded application."""
    ground_truth_path = REPO_ROOT / "data" / "ground_truth.json"
    manifest = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    rawad = next(s for s in manifest["smes"] if s["company_name"] == RAWAD_COMPANY)
    seeded_app_id = rawad["application_id"]

    res = svc.table(AGENT_RESULTS_TABLE).select("extracted_documents").eq(
        "application_id", seeded_app_id
    ).limit(1).execute()
    docs = res.data[0]["extracted_documents"]
    return seeded_app_id, docs, rawad["documents"]  # type: ignore[return-value]


def main() -> int:
    svc = get_service_client()
    seeded_app_id, seed_docs, ground_truth_docs = find_rawad_seed(svc)
    print(f"Source: seeded Rawad application {seeded_app_id} ({len(seed_docs)} documents)")

    server, server_log = start_server()
    new_application_id: str | None = None
    uploaded_storage_paths: list[str] = []

    try:
        # Generous read timeout: 20 sequential real vision calls plus forensic
        # LLM calls can take a while per request even though the server
        # itself stays responsive throughout (verified manually — /status
        # answers in ~1-2s at any point during a run).
        timeout = httpx.Timeout(10.0, read=180.0)
        sme_token = sign_in(RAWAD_EMAIL)
        bank_token = sign_in(BANK_EMAIL)
        sme = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {sme_token}"}, timeout=timeout)
        bank = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {bank_token}"}, timeout=timeout)

        # 1. fresh draft application
        r = sme.post("/applications", json={"requested_amount": 750_000})
        r.raise_for_status()
        new_application_id = r.json()["application_id"]
        print(f"Created draft application {new_application_id}")

        # 2. render + upload the batch
        for doc in seed_docs:
            png_bytes = render_receipt_image(doc)
            files = {"file": (f"{doc['document_id']}.png", png_bytes, "image/png")}
            r = sme.post(f"/applications/{new_application_id}/documents", files=files)
            r.raise_for_status()
        print(f"Uploaded {len(seed_docs)} document images")

        doc_rows = svc.table(DOCUMENTS_TABLE).select("file_url").eq(
            "application_id", new_application_id
        ).execute().data or []
        uploaded_storage_paths = [row["file_url"] for row in doc_rows]

        # 3. process
        r = sme.post(f"/applications/{new_application_id}/process")
        r.raise_for_status()
        print("POST /process accepted; polling /status ...")

        # 4. poll (a fresh connection per attempt, with one retry, so a single
        # transient read hiccup on a long-running pipeline doesn't abort the
        # whole run — the server itself is verified responsive throughout).
        deadline = time.time() + STATUS_POLL_TIMEOUT_S
        status_payload = None
        while time.time() < deadline:
            for attempt in range(2):
                try:
                    r = sme.get(f"/applications/{new_application_id}/status")
                    r.raise_for_status()
                    status_payload = r.json()
                    break
                except httpx.TimeoutException:
                    if attempt == 1:
                        raise
                    print("  (status poll timed out, retrying once)")
            print(f"  status={status_payload['status']} "
                  f"nodes_completed={status_payload['nodes_completed']} "
                  f"progress={status_payload['progress']:.2f}")
            if status_payload["progress"] >= 1.0:
                break
            time.sleep(STATUS_POLL_INTERVAL_S)
        else:
            raise SmokeTestError(f"pipeline did not finish within {STATUS_POLL_TIMEOUT_S}s")

        # /process leaves applications.status at "processing" (submit is a
        # separate SME action) — flip it to review_ready so the bank
        # endpoint's ownership-agnostic read still reflects a real run.
        svc.table(APPLICATIONS_TABLE).update({"status": "review_ready"}).eq(
            "id", new_application_id
        ).execute()

        # 5. bank read
        r = bank.get(f"/bank/applications/{new_application_id}")
        r.raise_for_status()
        detail = r.json()

        # --- Sanity check: real extraction, not defaulted zeros ---
        extracted = detail["extracted_documents"]
        zero_amount = [d for d in extracted if d["extracted_amount"] == 0.0]
        no_vendor = [d for d in extracted if not d.get("vendor")]
        print(f"\nExtracted {len(extracted)} documents "
              f"({len(zero_amount)} zero-amount, {len(no_vendor)} vendor-less)")
        if len(zero_amount) > len(extracted) // 2:
            raise SmokeTestError(
                "Vision extraction looks broken: majority of documents extracted as zero-amount."
            )

        # --- Forensic acceptance criteria ---
        forensic = detail["forensic_report"]
        if forensic is None:
            raise SmokeTestError("forensic_report is null — forensic_accountant_node did not run.")

        print(f"\nForensic report: overall_status={forensic['overall_status']} "
              f"reconciliation_rate={forensic['reconciliation_rate']:.3f}")
        for flag in forensic["discrepancy_flags"]:
            print(f"  [{flag['severity']}] {flag['description']}")

        fabricated_gt = next(d for d in ground_truth_docs if d["bucket"] == "fabricated")
        mismatch_gt = [d for d in ground_truth_docs if d["bucket"] == "mismatch"]

        high_flags = [f for f in forensic["discrepancy_flags"] if f["severity"] == "high"]
        medium_flags = [f for f in forensic["discrepancy_flags"] if f["severity"] == "medium"]

        if forensic["overall_status"] != "red":
            raise SmokeTestError(
                f"Expected overall_status='red' (fabricated invoice present), got "
                f"{forensic['overall_status']!r}."
            )
        if not high_flags:
            raise SmokeTestError("Expected at least one high-severity (fabricated) flag; found none.")
        if not medium_flags:
            raise SmokeTestError("Expected at least one medium-severity (mismatch) flag; found none.")
        if not (0.75 <= forensic["reconciliation_rate"] <= 0.95):
            raise SmokeTestError(
                f"reconciliation_rate {forensic['reconciliation_rate']} is not close to the "
                f"expected ~0.85 (17/20 clean)."
            )

        print(f"\nAcceptance check: fabricated invoice ({fabricated_gt['reason'][:60]}...) "
              f"-> RED via {len(high_flags)} high flag(s)")
        print(f"Acceptance check: {len(mismatch_gt)} genuine-mismatch invoice(s) "
              f"-> YELLOW-severity via {len(medium_flags)} medium flag(s)")
        print(f"Acceptance check: reconciliation_rate={forensic['reconciliation_rate']:.3f} (~0.85 expected)")
        print(f"Acceptance check: overall_status={forensic['overall_status']} (red expected)")
        print("\nSMOKE TEST PASSED")
        return 0

    finally:
        # --- cleanup: delete everything this run created ---
        if new_application_id:
            print(f"\nCleaning up application {new_application_id} ...")
            if uploaded_storage_paths:
                try:
                    svc.storage.from_(BUCKET).remove(uploaded_storage_paths)
                except Exception as exc:
                    print(f"  warning: storage cleanup failed: {exc}")
            svc.table(DOCUMENTS_TABLE).delete().eq("application_id", new_application_id).execute()
            svc.table(AGENT_RESULTS_TABLE).delete().eq("application_id", new_application_id).execute()
            svc.table(APPLICATIONS_TABLE).delete().eq("id", new_application_id).execute()

            remaining_docs = svc.table(DOCUMENTS_TABLE).select("id").eq(
                "application_id", new_application_id
            ).execute().data
            remaining_app = svc.table(APPLICATIONS_TABLE).select("id").eq(
                "id", new_application_id
            ).execute().data
            if remaining_docs or remaining_app:
                print("  warning: cleanup verification found leftover rows")
            else:
                print("  cleanup verified: no leftover rows")

        stop_server(server, server_log)
        print("uvicorn stopped")
        if SERVER_LOG_PATH.exists():
            tail = SERVER_LOG_PATH.read_text(encoding="utf-8", errors="replace")
            out = sys.stdout
            safe_tail = tail[-4000:].encode(out.encoding or "utf-8", errors="replace").decode(
                out.encoding or "utf-8", errors="replace"
            )
            print(f"\n--- server log ({SERVER_LOG_PATH}) ---")
            print(safe_tail)


if __name__ == "__main__":
    sys.exit(main())
