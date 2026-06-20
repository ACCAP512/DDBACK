# PROGRESS.md — running log

Newest first. Short entries: done / next / blocked.

## 2026-06-20 (broker-OS build — M2: auth & RBAC)
- **Done (M2, per `docs/BUILD_PLAN.md` §5):**
  - **Structural tenant isolation at the data-access layer** (`server/db/scoping.py`): a SQLAlchemy
    `do_orm_execute` hook injects `WHERE tenant_id = <principal>` into **every** ORM SELECT for every
    tenant-owned model via `with_loader_criteria` — so a forgotten filter cannot leak another tenant's
    rows (isolation is structural, not route discipline). To make one predicate cover everything,
    `tenant_id` was **denormalized onto Program/Claim/ChecklistItem** (migration M2). Unscoped/system
    sessions (seam, migrations, login) are unaffected; explicit `skip_tenant_filter` opt-out for login.
  - **Auth core:** argon2id password hashing (`auth/passwords.py`), JWT access tokens (`auth/tokens.py`,
    secret from `DRAWBACK_JWT_SECRET`, per-process ephemeral fallback in dev), the `Principal`
    (`auth/context.py`), and user provisioning/authentication (`auth/service.py`).
  - **RBAC** (`auth/rbac.py`): Admin · Preparer · Reviewer · **Signer** · Client → permission sets. The
    licensed-filer sign-off gate maps to `claims:sign`, held only by Signer (+ Admin).
  - **Auth API** (`api/deps.py` + routers): `POST /api/auth/login`, `GET /api/auth/me`, tenant-scoped
    `GET /api/clients` (client-role narrowed to its importer), tenant-scoped `GET /api/claims/{id}`, and
    **Signer-only** `POST /api/claims/{id}/signoff` (reuses the engine's `filing.signoff` attestation;
    audited). `get_scoped_db` binds the principal so every query is isolated.
  - **Tests (+12 → 137 green):** argon2 hash/verify + JWT roundtrip/tamper/expiry; structural isolation
    (a naive `select(Model)` and `get()` both return only the bound tenant; unscoped sees all; opt-out
    works); end-to-end RBAC over HTTP (login, `/me`, preparer-signoff→403, signer-signoff→200,
    incomplete-attestation→422, cross-tenant claim→404, clients list scoped). Engine's 112 untouched.
  - Deps added + recorded (argon2-cffi, PyJWT — both MIT) in `requirements.txt`/`THIRD-PARTY-NOTICES.md`/
    `sbom.json`. Alembic M2 migration chained on M1; `make migrate` builds the full M0→M2 chain.
- **Next:** **M3** — portfolio cockpit & work-queue home (claims-by-status, exception lanes, the 5-year
  clock; react-router + auth UI; the existing estimate/glass-box/defensibility/filing views become the
  claim-detail tabs). **Blocked:** none. (Deferred to where they belong: full client-portal row-scoping
  for claims via program join → M3; encryption-at-rest + retention → M4 when documents flow; a production
  org-selector for same-email-across-tenants login.)

## 2026-06-20 (broker-OS build — M1: persistence spine + the DESIGNATION LEDGER)
- **Done (M1, per `docs/BUILD_PLAN.md` §5/§8 — the P0 correctness core):**
  - **Designation ledger** (`server/domain/ledger.py`): per import line, summed across **all** claims
    over **all** time, `available → designated → remaining` (qty **and** duty). `assert_capacity_available()`
    **raises** `OverDesignationError` if a persist would push any import/export line past its imported/
    exported quantity — double-drawback (19 U.S.C. 1313(v)) is now *structurally impossible to persist*,
    not merely warned. Computed from natural keys, writing nothing, so a violation rolls back clean.
  - **Shared line identity:** `persist_estimate` now **upserts** import/export lines by natural key
    ((client, entry, line) / (client, reference)), so a new claim designates against the *same* rows prior
    claims used — the prerequisite that makes cross-claim conservation real. Designations persist
    `per_unit_designated_duty` (constant per line ⇒ duty conservation follows quantity).
  - **Claim status ledger** (`server/domain/status.py`): `transition_claim()` validates the lifecycle
    (draft→ready→filed→under_review→liquidated→paid + lawful step-backs), stamps timestamps, records the
    liquidated/paid **true-up** (`actual_refund`), and **audits every change**; illegal transitions raise
    (`InvalidTransitionError`) and mutate nothing.
  - **Schema:** Alembic M1 migration (chained on M0) adds the duty column + export unique constraint;
    verified upgrade/downgrade round-trip; `make migrate` builds the full chain.
  - **Tests (+9 → 125 green):** the per-line ledger view (qty+duty), Σ-across-claims, over-designation
    raises on **both** import and export sides (exact-fill fits, +1 raises), end-to-end double-claim blocked
    with nothing partial; full status lifecycle sets timestamps/money + audits each step, illegal transitions
    rejected. Engine's 112 untouched. End-to-end demo: claim $137,696.51 est / $11,875.48 defensible, a fully-
    designated line shows remaining 0 / $0, lifecycle draft→paid with a complete audit trail.
- **Next:** **M2** — auth & RBAC (argon2 + JWT; tenant isolation at the data-access layer; roles
  Admin/Preparer/Reviewer/**Signer**/Client; signer-only sign-off). **Blocked:** none. (Hardening follow-up:
  a DB-level trigger as defense-in-depth behind the service invariant; concurrency/locking for the ledger
  check under simultaneous writers.)

## 2026-06-19 (broker-OS build — M0: foundation & scaffolding)
- **Done (M0, per `docs/BUILD_PLAN.md` §5/§8):** stood up the new `server/` application layer *around* the
  untouched engine. Additive only — `engine/drawback/` and its 112 tests are unchanged.
  - **`server/` package:** `db · domain · auth · ocr · workflow · reports · services · api · worker.py`
    (auth/ocr/workflow/reports are M2–M6 placeholders). Path bootstrap makes `import drawback` work however
    the app is launched. Minimal FastAPI app (`server/api/main.py`, `/api/health` + `/api/readiness`).
  - **Domain schema (§3 spine) as SQLAlchemy 2.0 models** — Tenant·User·Client·Program·Claim·**Designation**·
    ImportEntryLine·ExportLine·Document·ChecklistItem·Task·AuditEvent (12 tables). Lossless `Money` type
    (Decimal-as-string; SQLite can't bind Decimal), portable `VARCHAR+CHECK` enums, string-UUID PKs,
    deterministic constraint naming convention (clean Alembic + SQLite-batch ALTERs).
  - **Alembic** wired (`alembic.ini` + `server/db/migrations/`), first migration autogenerated; `render_item`
    hook emits the custom `Money` import so migrations run as written. `make migrate` = `alembic upgrade head`;
    verified upgrade→downgrade→upgrade round-trip.
  - **Engine seam** (`server/services/engine_seam.py`): `run_estimate` (ingest→build_estimate→harden, strict)
    + `persist_estimate` (Estimate → Claim + Designations + import/export lines + AuditEvent). One-way
    dependency (app → engine) preserved.
  - **Tests (+4 → 116 green):** M0 smoke round-trip (real demo ingest → persisted claim; \$137,696.51 headline
    reconciles, money stays exact Decimal, reloads from a fresh session); **engine-purity guard** (asserts
    `engine/drawback/` imports stdlib-only — the moat lock); alembic-builds-schema regression.
  - Permissive deps added + recorded (SQLAlchemy/alembic MIT, pg8000 BSD) in `requirements.txt`,
    `THIRD-PARTY-NOTICES.md`, `sbom.json`. Existing demo API (`api/main.py`) + `make run` unchanged.
- **Next:** **M1** — the persisted **designation ledger**: per-import-line `available→designated→remaining`
  (qty + duty) with the across-claim / across-time over-designation invariant that **raises** (19 U.S.C.
  1313(v)), the claim status ledger, and engine-grade conservation tests. (M0 deliberately stopped before the
  ledger invariant.) **Blocked:** none.

## 2026-06-19 (monetization + compliance + product-readiness "Option B")
- **Strategy:** owner is unlicensed, no customers, $0 budget, won't raise, open to selling. Research →
  `docs/MONETIZATION.md` (sell/license to funded AI entrants / brokers; flat-fee only). Legal research →
  `docs/COMPLIANCE.md`: CBP HQ H350722 (Jan 2026) confirms **selling/licensing is the clean path**;
  operating it unlicensed would be customs business. Data: local/no-retention (already so) keystone for EEI
  confidentiality. IP: public-domain law + permissive deps + AI-assisted-but-assignable → clean, title clear
  (built solo, not employed).
- **Done (readiness build, compliant-by-design, all committed):**
  - **Correctness hardening** `defensibility.py`: structurally [VERIFIED]-only defensible headline +
    reconciliation invariant (raises, never clamps) + per-claim defensibility report; `/api/defensibility`.
  - **Licensed-filer sign-off gate** `filing/signoff.py`: `submit` 428s until a lawful operator attests.
  - **Real-format ingestion** `drawback/ingest/`: NetSuite spine × CBP 7501/ACE + AES/EEI overlay →
    engine contract; demo dataset; `make demo` (ingest→estimate→defensibility→signed claim); `/api/estimate/demo`.
  - **IP/diligence pack** (LICENSE, THIRD-PARTY-NOTICES, AI-DISCLOSURE, sbom.json) + **legal/** templates
    (EULA/DPA/privacy — attorney drafts).
  - Full suite **112 green**. Demo: best \$137.7K / audit-defensible \$11.9K, reconciliation OK.
- **In flight:** frontend compliance UI (estimate-not-promise + defensible-number lead, disclaimers + EULA
  gate, defensibility report view, sign-off form gating submit).
- **Next:** verify the frontend in-browser; update README. **Blocked:** none (attorney finalization of
  EULA/DPA and the employment/title items are owner actions, documented).


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
