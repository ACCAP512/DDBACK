# Drawback Engine

**Instant, glass-box duty-drawback eligibility.** Connect or upload your import/export data and see a
defensible U.S. duty-drawback recovery estimate on screen in seconds — with every claimed dollar traced
to the import it came from, the export that justifies it, the rule that makes it eligible, and a
confidence level.

> ⚠️ **Preparation & decision-support only.** This tool *prepares and estimates*. It is **not** the filer
> of record and **not** legal advice. A drawback claim must be certified and transmitted by the claimant
> or a licensed customs broker/attorney via ACE/ABI (19 CFR 190.6). Every CBP-connected step here is
> **simulated** and clearly marked. All bundled data is **synthetic**.

## What this is

A **complete, correctness-first system built solo** — a pure-stdlib decision engine wrapped in a
multi-tenant web app — published **source-available for review** ([`LICENSE`](LICENSE); all rights
reserved, not open-source). It's a working artifact and portfolio piece, not a live commercial service.

**Notable engineering:**
- An **exact integer min-cost-max-flow matcher**, hand-rolled and **validated against brute force**, that
  assigns exports to duty-paid imports to maximize recovery under the legal constraints — with a
  human-readable **trace for every claimed dollar**.
- A **pure-Python-stdlib engine core** (money in `decimal.Decimal`, zero third-party deps) so the legal
  logic is fully auditable — plus a **158-test** suite (ground-truth, rule, adversarial, reconciliation,
  property, performance).
- Legal rules rebuilt from **primary sources**, each tagged `[VERIFIED]/[INFERRED]/[GUESS]` with citations
  carried into every trace; the engine is **conservative** (ambiguity lowers the number, never inflates it).
- A **multi-tenant app layer** (FastAPI + SQLAlchemy) with **structural tenant isolation**, RBAC, a
  mandatory licensed-filer **sign-off gate**, and a persisted **designation ledger** that makes
  double-claiming (19 U.S.C. 1313(v)) structurally impossible across claims and over time.
- A worked-through **compliance & IP posture** ([`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)) and
  attorney-ready legal templates ([`legal/`](legal/)).

*The encoded law is public-domain; the dependency tree is permissive; all bundled data is synthetic.
Available for licensing or acquisition — see [`LICENSE`](LICENSE). Working codename; naming was out of scope.*

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

The React SPA is now the **broker OS** — the multi-tenant cockpit built around the engine
(`docs/BUILD_PLAN.md`; milestones M0–M3 done). Stand it up:

```bash
make setup     # venv + Python deps + build the SPA + generate sample data
make seed      # reset + seed a demo broker book-of-business into the dev DB
make server    # serve the broker-OS API + SPA at http://localhost:8001
```
Open **http://localhost:8001** and sign in (password `drawback`): `admin@northstar.test` (full access),
`signer@northstar.test` (can certify), or `client@northstar.test` (read-only, one importer). You land on
the **work queue** — triage lanes, the **5-year expiring-value clock**, and per-client accrued $ — then open
any claim to its tabs: **Overview** (lifecycle + sign-off), **Glass-box** (every matched pair + its trace),
**Ledger** (available → designated → remaining), and **Audit**.

See the engine's single-claim pipeline end-to-end on **real-format ingested data** (NetSuite + CBP 7501/ACE
+ AES/EEI → estimate → defensibility → signed claim):
```bash
make demo                     # engine CLI; also at the legacy estimator API: make run (:8000)
```

Dev mode (hot-reload frontend):
```bash
make server                   # broker-OS API + SPA on :8001
# in another shell:
cd web && npm run dev         # Vite on :5173, proxies /api -> :8001
```

Run the tests (158, all green — engine 112 + broker-OS app layer 46):
```bash
make test                     # pytest — engine correctness + app-layer suite
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
