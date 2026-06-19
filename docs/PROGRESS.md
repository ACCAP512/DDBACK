# PROGRESS.md — running log

Newest first. Short entries: done / next / blocked.

## 2026-06-19 (UX research + execution)
- **Done:** Ran 6 parallel primary-source UX/UX-research streams (NN/g, Baymard, WCAG 2.2, Google PAIR,
  peer-reviewed uncertainty-viz, design-system docs, competitor teardown) → `docs/UX_RESEARCH.md`
  (validated the build, compared options, recommended the best fit). Then **executed** the prioritized
  recommendations in `web/` (verified in-browser, both themes, no console errors; clean `npm install &&
  npm run build` green):
  - **Theme:** tokenized light/dark; **light is now the default**, dark a persisted toggle (WCAG-tuned both).
  - **Accessibility:** Radix primitives under the custom CSS (Dialog trace-drawer w/ focus-trap, Tabs nav,
    Popover/DropdownMenu filters, Tooltip), skip-link, focus-visible rings, prefers-reduced-motion, ≥24px
    targets, color+icon+label status (WCAG 2.2 AA pass, token-level contrast checked).
  - **Glass-box table → TanStack:** recovery-sorted, faceted batch filters w/ counts + chips, pagination
    (persisted), density toggle, virtualization, value-suppressed low-confidence rows, "Headline = Σ …
    reconciles four ways" badge + "Showing $Y of $X" line, Saved Views.
  - **Trace:** two-level disclosure (gist + Radix tabs Computation/Citations/Evidence/Assumptions),
    bound-action confidence, evidence count, prev/next, **live eCFR/Cornell citation links**, and a
    deep-linkable **`#/pair/<id>` standalone printable page**.
  - **Conservatism as headline:** "Audit-defensible — we left $X out / flagged N" framing, cliff-effect-safe
    range labels, frequency framing, two-tier number formatting (abbreviated hero/tiles + tooltip; full
    precision in ledger/trace).
  - **Upload/onboarding:** CSV templates + "Download example", dropzone privacy line, row-accounting banner,
    full-screen results skeleton.
- **Next:** optional P3 (correctable assumption chips, quantile-dotplot uncertainty viz, Recharts swap) —
  deferred. **Blocked:** none.

## 2026-06-19 (build complete)
- **Done:** M5 frontend (React+TS+Vite SPA) built green and **verified in-browser** end-to-end across all
  three layers: Layer 1 hero ($3.79M point / $1.68M low / +$0.52M pending) + range bar + by-year SVG chart +
  by-program/HTS splits + blocked-recovery panel (IEEPA→CAPE callout) + filing checklist + data quality;
  Layer 2 pairs table + full trace drawer (numbered derivation, citations incl. corrected 190.32(b)(1),
  charge breakdown, import→export→claim window, evidence manifest, assumption chips); Layer 3 SIMULATED
  ribbon + 2 valid CATAIR claims + record-typed transmission text + mock submit → manifest + lifecycle
  timeline. **No console errors.** Numbers reconcile throughout.
- **All 7 milestones complete; every Definition-of-Done item (PRD §10) met.** App runs via `make setup && make run`.
- **Next:** none required — build complete. (Future work tracked in LIMITATIONS.md: BOM manufacturing matching,
  windowed-transportation fast-path for mega-buckets, real HTSUS/ACE adapters, live filing.)

## 2026-06-19 (continued)
- **Done:** M2 data layer (models, dated tariff config, HTS reference fixture ~50 codes, synthetic
  generator, CSV parser + data-quality). M3 matching engine (exact Dijkstra+potentials MCMF validated vs
  brute force across 700 instances; two-pass headline/potential optimizer; per-pair traces). M4 estimate
  orchestration + FastAPI (sample/upload → estimate → glass-box pairs). M5 reconciliation + traces wired.
  M6 Layer-3 stub (CATAIR claim build/validate/mock-submit + simulated lifecycle). serialize.py. Samples
  committed. **59 tests green** (ground-truth, rule, adversarial, reconciliation, property, parser, perf,
  filing). README, LIMITATIONS, Makefile done.
- **Engine numbers (demo sample):** headline ≈ $3.79M point / $1.68M low, +$0.52M potential; reconciles
  to Σ breakdowns; blocked reasons surfaced (unused import duty, ineligible 232/IEEPA, missing proof, etc.).
- **In progress:** M5 frontend (React+TS+Vite SPA, Layers 1-3) — building via background subagent against
  the live API contract.
- **Next:** integrate + verify the SPA in-browser; WALKTHROUGH.md; final test pass + M7 hardening.
- **Blocked:** none.

## 2026-06-19
- **Done:** M0 scaffolding — repo `drawback-engine` (separate from surplus), venv + deps, `.gitignore`, `requirements.txt`,
  directory structure. M1 research gate — Phase 0 research run via 6 parallel primary-source agents; `RESEARCH.md` answers all
  18 §3.3 questions with citations + 10 headline corrections to PRD priors; `ASSUMPTIONS.md` (A-01..A-20 tagged); `DECISIONS.md`
  (D-001..D-011); `PLAN.md`.
- **Key research deltas driving the build:** §190.22/190.32 mapping is reversed from the PRD (C1); "other"-basket → 10-digit
  exception (C2); per-charge lesser-of, not flat 99% (C3); excise double-drawback cap is judicially dead (C6); IEEPA is out of
  drawback → CAPE (C7); importer self-file allowed but software can't certify (C8); retention 3-yr-from-liquidation (C9);
  "$15B unclaimed" is unsourced marketing, real paid ≈ $1B→$3.9B (C10).
- **Next:** M2/M3 — stdlib core: `models.py` → `config/tariff_eligibility.py` → `rules/*` → `matching/{mcmf,engine,trace}.py`
  → `data/{hts_reference,generator,parser}.py` → `estimate.py`, with pytest fixtures alongside.
- **Blocked:** none. (External seams documented, not blocking: no live ACE/ABI/CBP access → Layer 3 mock per D-009.)
