# DECISIONS.md — non-trivial choices, options, rationale

Append-only log. Each entry: the decision, options considered, what was picked, why. Deviations from the PRD
are logged here per PRD §0/§2.

---

### D-001 — Separate standalone repo, not inside `surplus/`
**Options:** (a) build inside the existing `surplus` repo; (b) new sibling repo `drawback-engine/`.
**Picked:** (b), at `/Users/achreki/Desktop/drawback-engine`, fresh `git init`.
**Why:** Entirely different product/domain (customs drawback vs. gov-auction surplus). The owner's established pattern is
separate standalone products that never cross-import. Keeps boundaries clean. (Naming is a working codename — PRD §0 says
naming is out of scope.)

### D-002 — Core engine is pure Python standard library
**Options:** (a) pandas + scipy/OR-Tools throughout; (b) pure-stdlib core, third-party only at the API edge.
**Picked:** (b). `engine/drawback/{models,config,rules,matching}` import **stdlib only** (`dataclasses`, `decimal`,
`datetime`, `csv`, `heapq`). Third-party deps (FastAPI/uvicorn/pytest) are app/test layer only.
**Why:** PRD demands the rules module be auditable, isolated, and "read like a spec," with no external paid deps and a
reproducible local run. A zero-dependency core eliminates version drift in the legal logic and makes every rule trivially
unit-testable. Cost: we hand-roll the optimizer (see D-004) and CSV handling instead of using libraries — acceptable and
arguably better for explainability.

### D-003 — Money in `decimal.Decimal`, quantized to cents
**Options:** float; integer cents; Decimal.
**Picked:** Decimal, ROUND_HALF_UP to cents, lesser-of and 99% applied before final quantization.
**Why:** Correctness is the prime directive; binary float silently corrupts duty math. Decimal is exact and readable.
(ASSUMPTION A-16.)

### D-004 — Matching = exact integer min-cost max-flow (transportation), decomposed per 8-digit HTS bucket
**Options:** (a) greedy heuristic (e.g., low-to-high); (b) LP via scipy/OR-Tools; (c) hand-rolled min-cost max-flow.
**Picked:** (c) — a successive-shortest-paths min-cost-flow with potentials (Johnson/Bellman-Ford init), exact **integer**
arithmetic on quantities, run **independently per (8-digit HTS bucket)** so each subproblem is small.
**Why:**
- **Correctness/optimality:** the objective ("maximize total recoverable duty subject to time windows, 8-digit match,
  per-unit lesser-of, and one-claim conservation") is a transportation/assignment problem. MCMF gives a provably optimal,
  integral assignment — no float wobble, no heuristic regret.
- **Explainability (a hard PRD requirement):** every unit of flow on an import→export arc is one matched pair with a clear
  per-pair recovery, rule, and confidence — the trace falls straight out of the flow decomposition.
- **Performance:** decomposing per HTS bucket keeps each MCMF instance tiny even when the whole dataset is large
  (PRD FR1.7); buckets are independent and embarrassingly parallel.
- **No dependency** (consistent with D-002).
**Validation plan:** the solver is checked against a brute-force optimum on small fixtures (property test) and against
hand-computed ground-truth fixtures. Deviation logged if brute force ever disagrees.
**Lesser-of inside flow:** per-pair arc "cost" = −(99% × min(designated per-unit eligible duty, comparator per-unit duty)).
Because the comparator differs for unused vs. manufacturing (A-03 vs. A-05), the arc-cost function is parameterized by
provision type; the two never share the comparator.

### D-005 — Stack: FastAPI backend serving a React + TypeScript (Vite) SPA
**Options:** (a) Streamlit/all-Python UI; (b) FastAPI + React/TS SPA; (c) full-stack TS.
**Picked:** (b). Python engine (correctness core) behind FastAPI; React+TS+Vite front end for the instant-feedback,
glass-box UX. FastAPI also serves the built SPA so a single process runs the whole app; a dev mode runs Vite separately.
**Why:** PRD names a React+TS SPA as the sensible default for the instant-feedback UX and warns against a templated look;
Python is the right home for the rules/optimization core. One-language UI (Streamlit) would compromise the "screenshot-
worthy, responsive" Layer-1 experience the thesis depends on.

### D-006 — Centralized, dated tariff-eligibility config
**Decision:** all time-sensitive eligibility (which charge types are drawback-eligible, AD/CVD exclusion, 232/IEEPA/122
status) lives in one module `config/tariff_eligibility.py` stamped `AS_OF = 2026-06-19`, surfaced in the UI.
**Why:** PRD §11 date-sensitivity guardrail; research shows this is the fastest-changing, most error-prone area. Unknown
charge types default to **ineligible** (conservative). (ASSUMPTION A-12/A-13.)

### D-007 — MVP drawback-type scope: unused (j)(1)/(j)(2) fully; manufacturing (a)/(b) encoded but partial
**Options:** build everything; build unused only; build unused + partial manufacturing.
**Picked:** unused merchandise **(j)(1) direct-ID and (j)(2) substitution** fully built, tested, and matched end-to-end
(the primary persona's re-export case and the cleanest linkage problem). Manufacturing **(a)/(b)** rules + the distinct
lesser-of comparator (A-05) + provision codes are encoded, but **BOM-based manufacturing matching is partial/stubbed** and
flagged in LIMITATIONS. Rejected **(c)** represented as a type only.
**Why:** Correctness over breadth (PRD §0). (j)(2) substitution exercises the whole hard core — 8-digit match, "other"
exception, lesser-of, conservation, tariff-layer exclusion, time windows — which is the moat. Manufacturing adds a BOM data
model that doesn't change the persona's headline materially and risks shipping a wrong number.

### D-008 — Conservatism realized as "headline vs. potential" partition
**Decision:** the engine computes a **headline (defensible)** number — only pairs that satisfy every verified rule with
sufficient proof and [VERIFIED]-grade assumptions — and a separate **potential (needs-review)** bucket for amounts blocked
by missing proof, out-of-window, ineligible duty layer, [INFERRED]/[GUESS] assumptions, or data-quality issues. The headline
range is `[headline_low, headline_point]`; potential is shown but never folded into the headline.
**Why:** Directly implements PRD §4.2 FR1.4/FR1.5/FR1.6 and the conservatism + honest-uncertainty principles.

### D-009 — Layer 3 is spec-shaped and mock-only
**Decision:** produce a CATAIR-shaped (record-typed) claim object + a fixed-width-ish serialization and a **mock submit** that
writes the would-be transmission to `filing_out/` and validates structure; never transmit to CBP. Lifecycle dashboard runs on
simulated status data behind a clean interface. Every seam marked "simulated — not connected to CBP" in code and UI.
**Why:** PRD §4.5/§7 — external blocker (no ABI filer code / license / ACE access). Clean seam so going live is contained.

### D-010 — Synthetic-data persona and labeling
**Decision:** primary synthetic persona = mid-market **electronics/industrial-hardware importer-exporter** importing
Section-301 Chinese components and re-exporting/exporting finished goods; generator emits realistic messiness (varied HTS,
multi-year spread, some out-of-window, some ineligible 232/IEEPA layers, some missing export proof, some "other"-basket HTS).
All synthetic data is clearly labeled and lives under `samples/`, isolated from any real-data path.
**Why:** PRD §5.2; exercises the eligible-vs-ineligible tariff logic and the conservatism partition so they are *visible*.

### D-011 — `[Updated]` C1 reversal honored: provision→regulation mapping
**Deviation from PRD:** PRD §3.2/§4.3 implied 190.22=unused, 190.32=manufacturing. Research (RESEARCH C1) found the reverse.
**Decision:** engine maps §1313(j)(2) unused → 19 CFR **190.32**; §1313(b) manufacturing → 19 CFR **190.22**. Logged as the
canonical mapping; the PRD's framing is superseded ("the research wins," PRD §0).
