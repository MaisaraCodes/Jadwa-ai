# Jadwa.ai — Synthetic Dataset (DATA.md)

This is the dataset the platform is demonstrated on. It is **synthetic by necessity and
by design**: real open-banking feeds and real SME financial documents are not available
to a hackathon team, so we generate a high-fidelity dataset modeled on real Saudi SME
financial patterns, with **SAMA's open-banking framework as the integration target** for
production. Every figure below is reproducible from a fixed seed.

## What's in it

| Layer | Contents |
|---|---|
| SME profiles | 6 businesses across logistics, café/F&B, construction supply, retail, and light manufacturing — each with a real Saudi district, a CR number, a backstory, and its own login. |
| Open-banking ledger | ~15 months of transactions per SME (`mock_open_banking_ledger`) — recurring revenue inflows, recurring costs (rent, payroll, and sector-specific costs like fuel or ingredients), and seasonality. This is the **ground truth** the forensic engine reconciles against. |
| Documents | A set of invoices / ZATCA receipts per SME (`agent_results.extracted_documents`), each carrying a real Base64 **TLV-encoded ZATCA QR** (tags 1–5: seller, VAT number, timestamp, total, VAT). |

## The point of the dataset: a designed fraud signal

Every SME's documents fall into three deliberately-constructed buckets, so the Forensic
Accountant has clean, checkable signal:

- **Legitimate** — a matching ledger debit exists within amount tolerance (±2%) and a ±5-day
  window → should clear **green**.
- **Fabricated** (1 per SME) — no matching ledger transaction at all → should flag **red**.
- **Genuine mismatch** (1–2 per SME) — a real timing gap or small amount difference; realistic
  bookkeeping noise, not fraud → should flag **yellow**.

Collectively the set exercises all three fraud signals the forensic node implements:
**(1)** no matching transaction, **(2)** amount mismatch beyond tolerance, and **(3)**
suspiciously round or repeated identical amounts.

## Reproducibility & auditability

- **Fixed random seed** — every run produces the identical dataset. Demos are repeatable.
- **`ground_truth.json` manifest** — for every document, records its bucket, its expected
  forensic flag, and a plain-language reason. This is how we (and the judges) can verify the
  system's output is *correct*, not just plausible — the flagged fakes are exactly the ones we planted.
- **Financial parameters are explicit** — revenue bands, cost structures, and seasonality per
  sector live in one config block, reviewed for realism by our economics lead.

## The demo hero record

**Rawad Logistics** (شركة رواد اللوجستية, Al-Kharj) is constructed so the forensic engine
reconciles **17 of 20** documents, with one fabricated **SAR 1,500.50** ZATCA receipt (12 Oct)
correctly flagged red and two timing/amount mismatches flagged yellow.

## Honest limitations

This is synthetic data, not a live bank feed. It is modeled on real Saudi SME financial
patterns and is designed to stress the same logic a production integration would face; it is
**not** drawn from real accounts. In production the same pipeline connects to real transaction
data under SAMA's open-banking licensing. Market-context data (SAMA / Monsha'at / GASTAT) used
by the Saudi Market Oracle is sourced separately and is out of scope for this dataset.
