# PROGRESS.md — running log

Newest first. Short entries: done / next / blocked.

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
