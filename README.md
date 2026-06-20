# Drawback Engine

**Instant, glass-box duty-drawback eligibility.** Connect or upload your import/export data and see a
defensible U.S. duty-drawback recovery estimate on screen in seconds — with every claimed dollar traced
to the import it came from, the export that justifies it, the rule that makes it eligible, and a
confidence level.

> ⚠️ **Preparation & decision-support only.** This tool *prepares and estimates*. It is **not** the filer
> of record and **not** legal advice. A drawback claim must be certified and transmitted by the claimant
> or a licensed customs broker/attorney via ACE/ABI (19 CFR 190.6). Every CBP-connected step here is
> **simulated** and clearly marked. All bundled data is **synthetic**.

**Compliant by design (see [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)).** The product is built to be
**sold or flat-fee-licensed** to a licensed customs broker/attorney or a self-filing importer — the lawful
path for an unlicensed software vendor (CBP HQ H350722). It enforces this in code: an estimate-not-promise
framing, a **structurally-defensible headline that rests only on [VERIFIED] legal rules**, and a
**mandatory licensed-filer sign-off** before any claim file is final. The go-to-market analysis is in
[`docs/MONETIZATION.md`](docs/MONETIZATION.md); attorney-ready EULA/DPA/privacy drafts are in [`legal/`](legal/).

*Working codename — naming is out of scope. Built per the Phase-0-gated PRD; see `docs/`.*

---

## What it does

Duty drawback refunds up to 99% of the duties/taxes/fees paid on imported goods that are later exported
or destroyed. It's widely under-claimed because the process is opaque and expert-gated. This engine
makes eligibility **instant** and **glass-box**:

- **Layer 1 — Instant eligibility:** data → an on-screen recovery estimate with a conservative **range**
  (defensible point + low end), broken down **by year, by HTS, by program**, plus **blocked-recovery
  reasons** and a **"what we'd need to file"** checklist.
- **Layer 2 — Glass box:** drill from the headline number → HTS → any matched **import↔export pair** and
  see the governing rule, the per-line computation, the eligible-vs-excluded charges, the 5-year window,
  and a confidence flag. Every level **reconciles** (the totals add up).
- **Layer 3 — Filing (stubbed):** produces a **CATAIR-shaped** claim file + a **mock submit** and a
  **simulated lifecycle** dashboard (accelerated-payment timing, liquidation, retention). Nothing is sent
  to CBP.

The heart is a **matching engine** that assigns exports to duty-paid imports to maximize recovery subject
to the verified rules (8-digit HTS substitution, the "lesser-of" cap, the 5-year window, one-claim
conservation, and exclusion of ineligible tariff layers), with an explainable trace per claimed dollar.

## Correctness first

This product prepares filings that, if wrong, expose a real importer to CBP penalties. So:
- The legal rules were rebuilt from **primary sources** (19 U.S.C. § 1313, 19 CFR Part 190, controlling
  case law, the ACE CATAIR) — see [`docs/RESEARCH.md`](docs/RESEARCH.md). Every encoded rule is tagged
  `[VERIFIED]/[INFERRED]/[GUESS]` in [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) and cited in each trace.
- The engine is **conservative**: ambiguity reduces the headline number, never inflates it. Missing
  proof, out-of-window, not-yet-liquidated, and ineligible duty layers are excluded from the headline and
  surfaced honestly.
- The optimizer is an **exact** integer min-cost-max-flow, **validated against brute force**. The money is
  `decimal.Decimal`. The test suite covers ground-truth, rule, adversarial, reconciliation, property, and
  performance cases.

## Quick start

Prereqs: Python 3.9+, Node 18+ (built on 3.9 / Node 25).

```bash
make setup     # venv + Python deps + build the React SPA + generate sample data
make run       # serve API + SPA at http://localhost:8000
```
Open **http://localhost:8000**, acknowledge the field-of-use gate, click **"Load sample data"**, and
you'll see the instant estimate (leading with the **audit-defensible** figure). Drill into any matched
pair in **Glass Box**, validate the number in the **Defensibility** tab (reconciliation + rules-fired with
citations), and sign off + mock-submit a claim in **Filing**.

End-to-end on **real-format ingested data** (NetSuite + CBP 7501/ACE + AES/EEI → estimate → defensibility
→ signed claim):
```bash
make demo
```

Dev mode (hot-reload frontend):
```bash
make dev                      # API on :8000
# in another shell:
cd web && npm run dev         # Vite on :5173, proxies /api -> :8000
```

Run the tests (112, all green):
```bash
make test                     # pytest — the engine's correctness suite
```

Regenerate the synthetic samples:
```bash
make samples
```

## Layout

```
engine/drawback/        Pure-stdlib engine core (auditable, dependency-free)
  config/               Dated tariff-eligibility config (the only time-sensitive knob)
  rules/                hts · time_windows · computation · eligibility · inventory  (read like a spec)
  matching/             mcmf (exact min-cost flow) · engine (two-pass optimizer) · trace
  data/                 hts_reference (local fixture) · generator (synthetic) · parser (CSV + DQ)
  ingest/               real-format ingestion: NetSuite spine × CBP 7501/ACE + AES/EEI overlay -> contract
  filing/               catair (stubbed claim file) · lifecycle · signoff (licensed-filer gate)
  assumptions.py        first-class A-01..A-23 registry (VERIFIED/INFERRED/GUESS + citations)
  defensibility.py      hardening: structural VERIFIED-only headline + reconciliation invariant + report
  estimate.py · serialize.py   orchestration: Dataset -> Estimate -> JSON
engine/tests/           112 tests: ground-truth, rule, adversarial, reconciliation, property, parser,
                        perf, defensibility, sign-off, ingestion
api/main.py             FastAPI: (sample|upload|demo) -> estimate -> glass-box -> defensibility -> signed filing
web/                    React + TypeScript + Vite SPA (Estimate · Glass Box · Defensibility · Filing)
samples/                synthetic CSVs + the real-format ingest demo (demo_netsuite / demo_customs)
scripts/                make_samples.py · demo.py (the make demo chain)
legal/                  EULA · DPA · privacy-policy templates (attorney drafts)
docs/                   RESEARCH · ASSUMPTIONS · DECISIONS · PLAN · PROGRESS · LIMITATIONS · WALKTHROUGH
                        · COMPLIANCE · MONETIZATION · UX_RESEARCH · INGESTION
```

The engine core imports **only the Python standard library** (money in `Decimal`, a hand-rolled exact
optimizer), so the legal logic is fully auditable with zero dependency drift. FastAPI/uvicorn/pytest are
app/test-layer only. See [`docs/DECISIONS.md`](docs/DECISIONS.md) for the why behind every choice.

## Honesty & limits

Read [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) for the full list. Highlights: the MVP fully builds
**unused-merchandise** drawback (§1313(j)(1)/(j)(2)); manufacturing (a)/(b) rules are encoded but BOM
matching is partial. Tariff eligibility is **date-stamped 2026-06-19** and must be re-verified before any
real use (it's centralized in one config module). The HTS reference is a local fixture, not a licensed
dataset. CBP/ACE transmission, real data ingestion at scale, and the licensed-filer workflow are
**designed and stubbed**, not live — each is a clean, documented seam.
