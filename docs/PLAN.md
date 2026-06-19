# PLAN.md — living build plan & milestone status

**Codename:** Drawback Engine · **As-of:** 2026-06-19 · Legend: ✅ done · 🔄 in progress · ⏳ next · ⬜ later

## Architecture (see DECISIONS D-002/D-004/D-005)
```
engine/drawback/          PURE STDLIB CORE (auditable, dependency-free)
  config/tariff_eligibility.py   dated charge-eligibility table (AS_OF gate)   [D-006, A-12/13]
  models.py                      ImportLine, ExportLine, MatchedPair, Trace, Estimate (dataclasses, Decimal)
  rules/hts.py                   8-digit match + "other"→10-digit exception     [A-01/02/04/20]
  rules/time_windows.py          5-yr import→claim window logic                 [A-09]
  rules/computation.py           99% + lesser-of (unused vs mfg comparators)    [A-03/05/06/11/16]
  rules/eligibility.py           charge eligibility, proof/liquidation gating   [A-12/14/15/19]
  rules/inventory.py             190.14 FIFO/LIFO/low-to-high/avg (direct-ID)   [A-08]
  matching/engine.py             per-bucket min-cost max-flow optimizer         [D-004, A-10]
  matching/mcmf.py               exact integer min-cost-flow primitive
  matching/trace.py              per-dollar explainability traces
  data/hts_reference.py          local HTS fixture (8-digit desc + "other" flag, duty rates)
  data/generator.py              synthetic persona datasets                     [D-010]
  data/parser.py                 CSV ingest + validation + data-quality report  [FR1.2]
  estimate.py                    orchestration: data -> Estimate w/ breakdowns  [FR1.3-1.6]
  filing/catair.py               CATAIR-shaped claim object + mock submit        [D-009, Layer 3]
  filing/lifecycle.py            simulated claim lifecycle states                [Q13]
engine/tests/                    ground-truth, rule, adversarial, reconciliation, property, perf
api/main.py                      FastAPI: upload/sample -> estimate -> claim/lifecycle JSON
web/                             React + TS + Vite SPA (Layer 1 magnet + Layer 2 glass box)
samples/                         committed synthetic datasets + fixtures
docs/                            RESEARCH, ASSUMPTIONS, DECISIONS, PLAN, PROGRESS, LIMITATIONS, WALKTHROUGH
```

## Milestones
- **M0 — Repo & scaffolding** ✅ structure, venv, .gitignore, requirements, tracking docs.
- **M1 — Research gate** ✅ RESEARCH.md (18 Qs cited) + ASSUMPTIONS.md (A-01..A-23 tagged). Engine logic unlocked.
- **M2 — Data layer** ✅ canonical models; HTS reference fixture (~50 codes); synthetic generator; CSV parser/validator + data-quality report; hand-verified fixtures.
- **M3 — Matching engine** ✅ rules modules (hts/time/computation/eligibility/inventory); exact MCMF primitive (validated vs brute force); two-pass per-bucket optimizer; per-pair traces.
- **M4 — Layer 1 instant eligibility** ✅ estimate orchestration; FastAPI; React SPA → sample/upload → headline + range + breakdowns (year/HTS/program) + blocked reasons + "what we'd need to file" + data-quality. Verified in-browser.
- **M5 — Layer 2 glass box** ✅ drill from headline → HTS → pair; reconciliation badge; full trace drawer (citations, numbered derivation, charge breakdown, window, evidence manifest, assumption chips); claim-package export. Verified in-browser.
- **M6 — Layer 3 stubbed** ✅ CATAIR-shaped claim build/validate; mock submit (writes + validates) + manifest; simulated lifecycle dashboard; all seams marked "SIMULATED". Verified in-browser.
- **M7 — Hardening & docs** ✅ 59 tests green; README + Makefile one-command run + seed data; WALKTHROUGH.md; LIMITATIONS.md; full in-browser end-to-end verification (no console errors).

**STATUS: build complete.** All seven deliverable layers built, tested, and verified running; every Definition-of-Done item (Section 10) met.

## Test strategy (PRD §9) — gates "done"
ground-truth fixtures (hand-computed) · one+ unit test per encoded rule · adversarial (double-claim / out-of-window /
near-miss HTS / 232+IEEPA mixed / missing proof / "other" basket) · reconciliation (headline == Σ breakdowns == Σ traces) ·
property (recovery ≤ eligible duty pool; claimed qty ≤ imported qty; monotonic; MCMF == brute force on small inputs) ·
conservatism (ambiguous fixture excluded from headline) · performance (FR1.7 on a large synthetic set).

## Current focus
🔄 M2/M3 — build the stdlib core (models → config → rules → MCMF → matcher → estimate) with tests alongside each module.
