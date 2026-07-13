"""
generate_synthetic_data.py — Jadwa.ai synthetic dataset (SYNTHETIC_DATA_SPEC.md).

Populates Supabase Postgres directly with a reproducible, convincing dataset:
  - sme_profiles           (one per SME, each linked to its own auth login)
  - applications           (one per SME, seeded past extraction)
  - mock_open_banking_ledger  (12-18 months of realistic transactions — GROUND TRUTH)
  - agent_results.extracted_documents (the invoices/receipts as DocumentJSON JSONB)

It also emits, into /data:
  - ground_truth.json      (which document_ids are fabricated/mismatch + why)  ← tests + narration
  - demo_credentials.json  (the seeded logins)  ← GITIGNORED, never commit
  - DATASET_SUMMARY.json   (counts, for the judge-facing DATA.md)

It does NOT write forensic_report / weakness_report / etc. — those are Phase-2 node
outputs. It does NOT touch market_knowledge_base (that's the Oracle corpus, Phase 3).

Run:  python data/generate_synthetic_data.py          (idempotent — safe to re-run)
      python data/generate_synthetic_data.py --reset  (explicitly clear prior seed first)

Env (backend/.env):
  DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  SEED_DEMO_PASSWORD   (optional; a default is used if unset — fine for a demo)

Deps: psycopg2-binary, supabase>=2.0, python-dotenv
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from supabase import create_client

# =====================================================================================
# CONFIG — knobs
# =====================================================================================
RANDOM_SEED = 42                # fixed → identical dataset every run (demos must repeat)
MONTHS_OF_HISTORY = 15          # 12-18
# These must stay inside the REAL forensic scoring tolerance
# (backend/nodes/forensic/scoring.py: AMOUNT_TOLERANCE_SAR=1.00 flat SAR,
# DATE_WINDOW_DAYS=3) or "legit" invoices fail their own clean-match check —
# a live end-to-end run caught this drifting out of sync once already.
AMOUNT_JITTER_SAR = 0.50        # legit invoices get a matching debit within ±0.50 SAR
DATE_WINDOW_DAYS = 2            # a ledger debit within ±1 day counts as a date "match"
CURRENCY = "SAR"
VAT_RATE = 0.15

# --- SALMAN: tune these financial parameters for realism ------------------------------
# Monthly revenue band + recurring monthly costs (SAR) per sector. Seasonality is a
# 12-length multiplier on revenue (index 0 = January). These drive how believable the
# ledger looks to a finance-literate judge — they're the numbers to sanity-check.
SECTOR_PROFILES = {
    "logistics": {
        "revenue": (180_000, 260_000),
        "costs": {"rent": 22_000, "payroll": 70_000, "fuel": 45_000},
        "seasonality": [0.9, 0.9, 1.0, 1.0, 1.05, 1.1, 1.15, 1.1, 1.0, 1.0, 0.95, 1.1],
    },
    "cafe": {
        "revenue": (70_000, 110_000),
        "costs": {"rent": 18_000, "payroll": 28_000, "ingredients": 24_000},
        "seasonality": [1.0, 1.0, 1.05, 1.1, 1.15, 0.85, 0.8, 0.8, 1.0, 1.1, 1.15, 1.2],
    },
    "construction_supplier": {
        "revenue": (220_000, 340_000),
        "costs": {"rent": 30_000, "payroll": 85_000, "materials": 120_000},
        "seasonality": [1.1, 1.15, 1.2, 1.1, 1.0, 0.85, 0.8, 0.85, 1.0, 1.1, 1.15, 1.1],
    },
    "retail": {
        "revenue": (95_000, 150_000),
        "costs": {"rent": 25_000, "payroll": 32_000, "stock": 55_000},
        "seasonality": [1.0, 1.0, 1.05, 1.1, 1.2, 1.0, 0.9, 0.9, 1.0, 1.05, 1.15, 1.3],
    },
    "manufacturer": {
        "revenue": (160_000, 240_000),
        "costs": {"rent": 28_000, "payroll": 78_000, "raw_materials": 70_000},
        "seasonality": [1.0, 1.0, 1.05, 1.05, 1.1, 1.05, 0.95, 0.95, 1.05, 1.1, 1.05, 1.0],
    },
}

# --- Personas. Rawad Logistics is the demo hero (matches the bank mockup). -------------
# `docs` = (legit, fabricated, mismatch). Rawad is pinned to 20 docs → 17 green / 1 red / 2 yellow
# so the forensic node computes reconciliation 17/20 = 0.85 (matches the mockup + schema example).
PERSONAS = [
    {
        "key": "rawad", "company_name": "Rawad Logistics", "company_name_ar": "شركة رواد اللوجستية",
        "sector": "logistics", "district": "Al-Kharj", "cr_number": "1010482913",
        "established_year": 2019, "requested_amount": 750_000,
        "backstory": "Family-run last-mile logistics operator; 80% of fuel from a single vendor.",
        "docs": (17, 1, 2), "email": "mohammed@rawad-logistics.sa.demo",
    },
    {
        "key": "nakhla", "company_name": "Nakhla Specialty Coffee", "company_name_ar": "نخلة للقهوة المختصة",
        "sector": "cafe", "district": "Al-Malqa, Riyadh", "cr_number": "1010773204",
        "established_year": 2021, "requested_amount": 300_000,
        "backstory": "Two-branch specialty café; strong seasonality, tight cash buffer.",
        "docs": (6, 1, 1), "email": "owner@nakhla-coffee.sa.demo",
    },
    {
        "key": "binsahl", "company_name": "Bin Sahl Building Materials", "company_name_ar": "بن سهل لمواد البناء",
        "sector": "construction_supplier", "district": "Al-Sulay, Riyadh", "cr_number": "1010556188",
        "established_year": 2016, "requested_amount": 1_200_000,
        "backstory": "Cement and rebar supplier to mid-size contractors; lumpy receivables.",
        "docs": (7, 1, 1), "email": "finance@binsahl-materials.sa.demo",
    },
    {
        "key": "waseet", "company_name": "Al-Waseet Retail", "company_name_ar": "الوسيط للتجزئة",
        "sector": "retail", "district": "Al-Olaya, Riyadh", "cr_number": "1010299471",
        "established_year": 2018, "requested_amount": 400_000,
        "backstory": "Single-location electronics retailer; heavy Q4 concentration.",
        "docs": (6, 1, 1), "email": "manager@alwaseet-retail.sa.demo",
    },
    {
        "key": "midad", "company_name": "Midad Plastics", "company_name_ar": "مداد للبلاستيك",
        "sector": "manufacturer", "district": "2nd Industrial City, Riyadh", "cr_number": "1010641097",
        "established_year": 2015, "requested_amount": 900_000,
        "backstory": "Small injection-moulding manufacturer; stable but low margins.",
        "docs": (7, 1, 1), "email": "accounts@midad-plastics.sa.demo",
    },
    {
        "key": "durub", "company_name": "Durub Auto Parts", "company_name_ar": "دروب لقطع الغيار",
        "sector": "retail", "district": "Al-Naseem, Riyadh", "cr_number": "1010318852",
        "established_year": 2020, "requested_amount": 350_000,
        "backstory": "Auto-parts trader; repeated round-number cash purchases worth a second look.",
        "docs": (6, 1, 1), "email": "owner@durub-autoparts.sa.demo",
    },
]

BANK_LOGIN = {"email": "khalid@alinma.sa.demo", "display_name": "Khalid · Alinma"}
DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "Jadwa-Demo-2026!")

# --- SCHEMA KNOBS: confirmed against the live DB by introspection (2026-07-03) ---------
# applications.status enum (application_status) = draft, processing, review_ready,
# approved, rejected, more_info_needed — "submitted" is NOT a valid value.
# review_ready is the bank-queue equivalent: doc processing done, awaiting bank review.
SEEDED_APP_STATUS = "review_ready"       # MUST be a valid applications.status enum value
SME_PROFILES_TABLE = "sme_profiles"
APPLICATIONS_TABLE = "applications"
LEDGER_TABLE = "mock_open_banking_ledger"
AGENT_RESULTS_TABLE = "agent_results"
AGENT_RESULTS_PK = "application_id"
AGENT_RESULTS_DOCS_COL = "extracted_documents"

# mock_open_banking_ledger's REAL columns differ from the spec's suggested shape:
# id (pk, auto), cr_number, transaction_date (not "date"), description, amount,
# transaction_type (check: 'credit'|'debit'). No counterparty/running_balance columns.
# build_ledger_and_docs() below still produces cr_number/date/amount/counterparty/
# description/running_balance dicts (useful internally for computing running_balance
# and readable descriptions); persist_ledger_row() adapts each row to the real table.

DATA_DIR = Path(__file__).resolve().parent
VENDORS = ["ADNOC Fuel", "Saudi Diesel", "Al-Rajhi Supplies", "Almarai", "SABIC Polymers",
           "Binzagr Trading", "Jarir", "STC Business", "Saudi Electricity Co", "Nesma Contracting"]


# =====================================================================================
# Helpers
# =====================================================================================
def _round_amount(x: float) -> float:
    return round(x, 2)


def encode_zatca_tlv(seller: str, vat_number: str, timestamp: str, total: float, vat: float) -> str:
    """Base64 TLV per ZATCA Phase-2 tags 1-5 (SYNTHETIC_DATA_SPEC 'Synthetic ZATCA QR').
    Each field = tag byte + length byte + UTF-8 value. NOT a ZATCA API call — this is the
    real offline structure the forensic node decodes and validates."""
    fields = [
        (1, seller),
        (2, vat_number),
        (3, timestamp),
        (4, f"{total:.2f}"),
        (5, f"{vat:.2f}"),
    ]
    payload = b""
    for tag, value in fields:
        vb = str(value).encode("utf-8")
        payload += bytes([tag, len(vb)]) + vb
    return base64.b64encode(payload).decode("ascii")


def synthetic_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def make_document(rng, doc_id, vendor, amount, when: date, doc_type: str) -> dict:
    """A DocumentJSON row (models.py). zatca_receipt types carry a real TLV QR."""
    total = _round_amount(amount)
    vat = _round_amount(total - total / (1 + VAT_RATE))
    zatca_hash = None
    qr_base64 = None
    if doc_type == "zatca_receipt":
        vat_number = "3" + "".join(str(rng.randint(0, 9)) for _ in range(14))
        ts = datetime(when.year, when.month, when.day, rng.randint(8, 20), rng.randint(0, 59)).isoformat()
        qr_base64 = encode_zatca_tlv(vendor, vat_number, ts, total, vat)
        zatca_hash = synthetic_hash(qr_base64, doc_id)
    return {
        "document_id": doc_id,
        "type": doc_type,
        "vendor": vendor,
        "extracted_amount": total,
        "currency": CURRENCY,
        "date": when.isoformat(),
        "line_items": [f"{vendor} — {doc_type.replace('_', ' ')}"],
        "zatca_verification_hash": zatca_hash,
        "zatca_qr_base64": qr_base64,
        "confidence_score": round(rng.uniform(0.9, 0.99), 2),
    }


# =====================================================================================
# Generation
# =====================================================================================
def build_ledger_and_docs(rng, persona) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (ledger_rows, extracted_documents, ground_truth_entries) for one SME.
    Legit docs each get a matching ledger debit; fabricated get none; mismatch get a
    deliberately-off debit. Exercises all three fraud signals."""
    sector = SECTOR_PROFILES[persona["sector"]]
    cr = persona["cr_number"]
    n_legit, n_fab, n_mis = persona["docs"]

    ledger: list[dict] = []
    docs: list[dict] = []
    truth: list[dict] = []

    # month-start dates, oldest → newest
    base = date.today().replace(day=1)
    months = []
    for i in range(MONTHS_OF_HISTORY - 1, -1, -1):
        y = base.year + (base.month - 1 - i) // 12
        m = (base.month - 1 - i) % 12 + 1
        months.append(date(y, m, 1))

    # --- recurring background transactions (revenue in, costs out) ---
    for mstart in months:
        seas = sector["seasonality"][mstart.month - 1]
        revenue = _round_amount(rng.uniform(*sector["revenue"]) * seas)
        ledger.append(dict(cr_number=cr, date=mstart + timedelta(days=rng.randint(2, 7)),
                           amount=revenue, counterparty="Customer receipts",
                           description="Monthly revenue"))
        for name, amt in sector["costs"].items():
            jitter = _round_amount(amt * rng.uniform(0.95, 1.08))
            ledger.append(dict(cr_number=cr, date=mstart + timedelta(days=rng.randint(1, 26)),
                               amount=-jitter, counterparty=name.title(),
                               description=f"Recurring {name}"))

    def a_month(i_from_end=0):
        return months[-(1 + i_from_end)]

    # --- legit docs: each has a matching ledger debit within tolerance + window ---
    for _ in range(n_legit):
        d_id = str(uuid.uuid4())
        vendor = rng.choice(VENDORS)
        amount = _round_amount(rng.uniform(1_200, 18_000))
        when = a_month(rng.randint(0, 3)) + timedelta(days=rng.randint(1, 25))
        dtype = "zatca_receipt" if rng.random() < 0.5 else "invoice"
        docs.append(make_document(rng, d_id, vendor, amount, when, dtype))
        # matching debit (tiny jitter within tolerance, date within window)
        ledger.append(dict(cr_number=cr,
                           date=when + timedelta(days=rng.randint(-DATE_WINDOW_DAYS + 1, DATE_WINDOW_DAYS - 1)),
                           amount=-_round_amount(amount - rng.uniform(-AMOUNT_JITTER_SAR, AMOUNT_JITTER_SAR)),
                           counterparty=vendor, description="Supplier payment"))
        truth.append(dict(document_id=d_id, bucket="legit", expected_flag="green",
                          reason="Matching ledger debit within amount tolerance and date window."))

    # --- fabricated docs: NO ledger match at all (signal 1) ---
    for k in range(n_fab):
        d_id = str(uuid.uuid4())
        # Rawad's hero fabricated receipt is pinned to the mockup: SAR 1,500.50, 12 Oct.
        if persona["key"] == "rawad" and k == 0:
            vendor, amount = "Gulf Fuel Depot", 1500.50
            when = date(2025, 10, 12)
        else:
            vendor = rng.choice(VENDORS)
            amount = _round_amount(rng.uniform(2_000, 9_000))
            when = a_month(rng.randint(0, 2)) + timedelta(days=rng.randint(1, 25))
        docs.append(make_document(rng, d_id, vendor, amount, when, "zatca_receipt"))
        truth.append(dict(document_id=d_id, bucket="fabricated", expected_flag="red",
                          reason=f"No corresponding transaction in the ledger (fabricated). "
                                 f"QR parses as valid; {CURRENCY} {amount:.2f} on {when.isoformat()} "
                                 f"has no matching debit."))

    # --- mismatch docs: real but off — exercises signals 2 and 3 ---
    for k in range(n_mis):
        d_id = str(uuid.uuid4())
        vendor = rng.choice(VENDORS)
        when = a_month(rng.randint(0, 2)) + timedelta(days=rng.randint(1, 20))
        if k == 0:
            # signal 2: amount mismatch beyond tolerance (ledger debit off by ~10%)
            amount = _round_amount(rng.uniform(3_000, 12_000))
            docs.append(make_document(rng, d_id, vendor, amount, when, "invoice"))
            ledger.append(dict(cr_number=cr, date=when + timedelta(days=rng.randint(0, 3)),
                               amount=-_round_amount(amount * 0.9), counterparty=vendor,
                               description="Supplier payment (amount differs)"))
            truth.append(dict(document_id=d_id, bucket="mismatch", expected_flag="yellow",
                              reason="Ledger debit exists but amount differs ~10% (beyond tolerance) — bookkeeping noise."))
        else:
            # signal 3: suspiciously round / repeated identical amount
            amount = 5000.00
            docs.append(make_document(rng, d_id, vendor, amount, when, "invoice"))
            ledger.append(dict(cr_number=cr, date=when + timedelta(days=DATE_WINDOW_DAYS + rng.randint(3, 9)),
                               amount=-amount, counterparty=vendor,
                               description="Supplier payment (late posting)"))
            truth.append(dict(document_id=d_id, bucket="mismatch", expected_flag="yellow",
                              reason="Suspiciously round amount and posted outside the date window (late) — timing noise, not fraud."))

    # sort ledger by date, compute running balance
    ledger.sort(key=lambda r: r["date"])
    bal = 0.0
    for r in ledger:
        bal = _round_amount(bal + float(r["amount"]))
        r["running_balance"] = bal
        r["date"] = r["date"].isoformat()
    return ledger, docs, truth


# =====================================================================================
# Persistence
# =====================================================================================
def upsert_auth_user(sb, email: str, role: str, display_name: str) -> str:
    """Idempotent: return existing user id for email, else create it with role in app_metadata."""
    # page through admin list to find an existing user
    try:
        page = 1
        while True:
            res = sb.auth.admin.list_users(page=page, per_page=200)
            users = res if isinstance(res, list) else getattr(res, "users", res)
            if not users:
                break
            for u in users:
                if getattr(u, "email", None) == email:
                    return u.id
            if len(users) < 200:
                break
            page += 1
    except Exception:
        pass
    created = sb.auth.admin.create_user({
        "email": email, "password": DEMO_PASSWORD, "email_confirm": True,
        "app_metadata": {"role": role},
        "user_metadata": {"display_name": display_name, "role": role},
    })
    return created.user.id


def clean_previous(cur, sb, cr_numbers, emails):
    """Remove any prior seed so the run is reproducible/idempotent."""
    cur.execute(f"select a.id from {APPLICATIONS_TABLE} a "
                f"join {SME_PROFILES_TABLE} p on p.id = a.sme_profile_id "
                f"where p.cr_number = any(%s)", (cr_numbers,))
    app_ids = [r[0] for r in cur.fetchall()]
    if app_ids:
        cur.execute(f"delete from {AGENT_RESULTS_TABLE} where {AGENT_RESULTS_PK} = any(%s::uuid[])", (app_ids,))
        cur.execute(f"delete from {APPLICATIONS_TABLE} where id = any(%s::uuid[])", (app_ids,))
    cur.execute(f"delete from {LEDGER_TABLE} where cr_number = any(%s)", (cr_numbers,))
    cur.execute(f"delete from {SME_PROFILES_TABLE} where cr_number = any(%s)", (cr_numbers,))
    # delete prior demo auth users
    try:
        page = 1
        while True:
            res = sb.auth.admin.list_users(page=page, per_page=200)
            users = res if isinstance(res, list) else getattr(res, "users", res)
            if not users:
                break
            for u in users:
                if getattr(u, "email", None) in emails:
                    sb.auth.admin.delete_user(u.id)
            if len(users) < 200:
                break
            page += 1
    except Exception:
        pass


def main(reset: bool) -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")
    rng = random.Random(RANDOM_SEED)

    dsn = os.environ["DATABASE_URL"]
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    cr_numbers = [p["cr_number"] for p in PERSONAS]
    emails = [p["email"] for p in PERSONAS] + [BANK_LOGIN["email"]]

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    ground_truth = {"generated_at": datetime.now(timezone.utc).isoformat(), "seed": RANDOM_SEED, "smes": []}
    credentials = {"password": DEMO_PASSWORD, "bank": BANK_LOGIN["email"], "smes": {}}
    summary = {"n_smes": len(PERSONAS), "months_of_history": MONTHS_OF_HISTORY,
               "totals": {"ledger_rows": 0, "documents": 0, "fabricated": 0, "mismatch": 0, "legit": 0}}

    try:
        if reset:
            clean_previous(cur, sb, cr_numbers, emails)
            conn.commit()

        # bank login (idempotent) — needed to demo the bank side
        upsert_auth_user(sb, BANK_LOGIN["email"], "bank", BANK_LOGIN["display_name"])

        for persona in PERSONAS:
            # 1. auth login for this SME
            user_id = upsert_auth_user(sb, persona["email"], "sme", persona["company_name"])
            credentials["smes"][persona["company_name"]] = persona["email"]

            # 2. profile (idempotent on cr_number)
            cur.execute(
                f"insert into {SME_PROFILES_TABLE} (user_id, company_name, cr_number, sector, district) "
                f"values (%s,%s,%s,%s,%s) "
                f"on conflict (cr_number) do update set user_id = excluded.user_id, "
                f"company_name = excluded.company_name, sector = excluded.sector, district = excluded.district "
                f"returning id",
                (user_id, persona["company_name"], persona["cr_number"], persona["sector"], persona["district"]),
            )
            row = cur.fetchone()
            if row:
                profile_id = row[0]
            else:
                cur.execute(f"select id from {SME_PROFILES_TABLE} where cr_number = %s", (persona["cr_number"],))
                profile_id = cur.fetchone()[0]

            # 3. application
            cur.execute(
                f"insert into {APPLICATIONS_TABLE} (sme_profile_id, requested_amount, status) "
                f"values (%s,%s,%s) returning id",
                (profile_id, persona["requested_amount"], SEEDED_APP_STATUS),
            )
            application_id = cur.fetchone()[0]

            # 4. ledger + extracted documents
            ledger, docs, truth = build_ledger_and_docs(rng, persona)
            ledger_rows = [
                dict(
                    cr_number=r["cr_number"],
                    transaction_date=r["date"],
                    amount=r["amount"],
                    description=f"{r['description']} — {r['counterparty']}" if r["counterparty"] else r["description"],
                    transaction_type="credit" if r["amount"] > 0 else "debit",
                )
                for r in ledger
            ]
            psycopg2.extras.execute_batch(
                cur,
                f"insert into {LEDGER_TABLE} (cr_number, transaction_date, amount, description, transaction_type) "
                f"values (%(cr_number)s,%(transaction_date)s,%(amount)s,%(description)s,%(transaction_type)s)",
                ledger_rows,
            )
            cur.execute(
                f"insert into {AGENT_RESULTS_TABLE} ({AGENT_RESULTS_PK}, {AGENT_RESULTS_DOCS_COL}) "
                f"values (%s, %s) on conflict ({AGENT_RESULTS_PK}) do update "
                f"set {AGENT_RESULTS_DOCS_COL} = excluded.{AGENT_RESULTS_DOCS_COL}",
                (application_id, json.dumps(docs)),
            )

            # 5. manifest + counts
            for t in truth:
                t["sme"] = persona["company_name"]
                t["application_id"] = application_id
            ground_truth["smes"].append({
                "company_name": persona["company_name"], "cr_number": persona["cr_number"],
                "sector": persona["sector"], "district": persona["district"],
                "application_id": application_id, "backstory": persona["backstory"],
                "documents": truth,
            })
            summary["totals"]["ledger_rows"] += len(ledger)
            summary["totals"]["documents"] += len(docs)
            for t in truth:
                summary["totals"][t["bucket"]] += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    # emit artifacts
    (DATA_DIR / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "demo_credentials.json").write_text(json.dumps(credentials, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "DATASET_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Synthetic dataset generated.")
    print(f"  SMEs: {summary['n_smes']} · ledger rows: {summary['totals']['ledger_rows']} · "
          f"documents: {summary['totals']['documents']} "
          f"(legit {summary['totals']['legit']}, fabricated {summary['totals']['fabricated']}, "
          f"mismatch {summary['totals']['mismatch']})")
    print(f"  Manifest → data/ground_truth.json · credentials → data/demo_credentials.json (gitignored)")
    print(f"  Demo password: {DEMO_PASSWORD}  ·  bank login: {BANK_LOGIN['email']}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console default (cp1252) can't print → · etc.
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="clear prior seed (profiles/apps/ledger/users) first")
    main(ap.parse_args().reset)
