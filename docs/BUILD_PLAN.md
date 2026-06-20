# BUILD_PLAN.md — the broker drawback OS

**Date:** 2026-06-19 · **Goal:** evolve the validated single-claim glass-box engine into a **multi-tenant
"arm-the-broker" drawback operating system** — the four layers from `UX_WORKFLOW_PLAN.md`: **Intake** (OCR
+ doc-match) → **Workbench** (reconciliation + per-type checklist + Gaps & Chase) → **Engine** (matcher +
VERIFIED-only defensible headline + designation ledger — *exists*) → **Book of business** (portfolio
cockpit, claim history, audit binder, client reports, RBAC). Sold flat-fee so the broker keeps the
portfolio. Build first; the sell-vs-operate endgame stays open (this build produces a far more valuable
asset either way).

> **What's already done (the moat — do NOT rebuild):** the pure-stdlib engine (`engine/drawback/`):
> models, rules, the exact MCMF matcher, `estimate`, `defensibility` (VERIFIED-only headline +
> reconciliation invariant + per-claim report), `assumptions`, real-format `ingest` (NetSuite × 7501/ACE ×
> AES/EEI), `filing` (CATAIR + lifecycle + licensed-filer `signoff`). 112 tests green. FastAPI + a React/TS
> SPA with the glass-box / defensibility / sign-off UI. The build below is the **application layer around
> this**, consuming the engine's public interfaces.

---

## 1. Architectural principles (non-negotiable)

1. **Keep the engine core pure-stdlib and untouched.** `engine/drawback/{models,config,rules,matching,
   assumptions,defensibility,estimate,serialize}` stay dependency-free and auditable. The new app layer
   *consumes* them (translates DB rows ↔ engine dataclasses); it never imports a DB into the engine. This
   preserves the moat, the test suite, and the clean-IP story.
2. **Additive, in a new `server/` layer.** All persistence, multi-tenancy, auth, OCR, and workflow live in a
   new package; the engine and its 112 tests are not modified.
3. **Permissive-only dependencies (protect the sellable IP — zero copyleft in shipped code).** See §4; flag
   every LGPL/GPL/AGPL touch and route around it (subprocess-only system tools, or a permissive alternative).
4. **Glass-box, VERIFIED-only, conservative, sign-off-gated — preserved end to end.** Every new surface
   (OCR extraction, designations, reports) inherits the `VERIFIED / needs-review` discipline. OCR *proposes*;
   a human *confirms*; the licensed signer *certifies*. Nothing auto-files.
5. **Local-first, secure, multi-tenant.** The data posture evolves from the estimator's "no-retention" to
   "the broker is the data controller and *retains* their book of business" (they need history + the audit
   binder). EEI confidentiality (15 CFR 30.60) is handled by **tenant isolation + encryption + the DPA
   (`legal/`) + local OCR by default** (client docs don't leave the tenant); a self-host/on-prem option for
   the most sensitive shops. *(This brings auth/multi-tenant/deployment — previously out of scope — in scope.)*
6. **Small, shippable milestones; each ends green.** Foundation (persistence + domain + designation ledger)
   before features. Build correctness-critical pieces (the ledger conservation) with the same rigor as the
   engine.

---

## 2. Target architecture

```
engine/drawback/         PURE STDLIB engine core — UNCHANGED (the moat)
server/                  NEW application layer (FastAPI app)
  db/                    SQLAlchemy 2.0 models + Alembic migrations (SQLite dev → Postgres prod)
  domain/                tenancy · clients · programs · claims · lines · DESIGNATION LEDGER · status ledger
  auth/                  users · password hashing · JWT sessions · RBAC (admin/preparer/reviewer/signer/client)
  ocr/                   pipeline: PDF→image (pypdfium2) → OCR (Tesseract) → classify → extract → match
  workflow/              per-type CHECKLIST engine · reconciliation · Gaps&Chase tasks · client requests
  reports/               client recovery report (PDF) + internal XLSX (expected-vs-actual)
  services/              the seam to engine/: dataset→estimate→defensibility→persisted designations
  api/                   FastAPI routers (supersedes today's single api/main.py)
  worker.py              background job runner (OCR + report generation)
web/                     React+TS+Vite SPA — EXPANDED: router + auth + portfolio/client/claim/docs
                         (reuses the existing estimate / glass-box / defensibility / filing views as the
                          "claim detail" tabs)
samples/ docs/ legal/    as today (+ new doc fixtures for OCR)
```

**Request → engine flow (persisted):** broker uploads docs → OCR/ingest builds a `Dataset` → `build_estimate`
+ `defensibility.harden` run → results persist as a **Claim + ClaimLines + Designations** → the **designation
ledger** updates each import line's `available → designated → remaining`. The matcher and defensibility code
are unchanged; their outputs are now *stored*, not ephemeral.

---

## 3. The domain data model (the P0 spine)

```
Tenant(org)            id, name, kind(broker_firm|self_filer), created
  └─ User              id, tenant_id, email, password_hash, name, role, client_scope_id?, active
  └─ Client(importer)  id, tenant_id, name, importer_id(EIN), notes
       └─ Program      id, client_id, name, drawback_type(j1|j2|a|b|c), config(json), mfg_ruling_ref
            └─ Claim   id, program_id, period, mode(retroactive|periodic),
                        status(draft|ready|filed|under_review|liquidated|paid),
                        filed_at, liquidated_at, paid_at,
                        estimated_refund, defensible_refund, actual_refund, claim_number, signoff(json)
  └─ ImportEntryLine   id, tenant_id, client_id, entry_number, line_no, hts10, import_date, quantity, uom,
                        entered_value, charges(json), liquidated, source_document_id
  └─ ExportLine        id, tenant_id, client_id, reference, hts10, export_date, quantity, uom,
                        value_per_unit, has_export_proof, itn, proof_document_id, direct_id_*
  └─ Designation ★     id, tenant_id, claim_id, import_entry_line_id, export_line_id, quantity, provision,
                        per_unit_recovery, recovery, recovery_low, confidence, in_headline, trace(json)
  └─ Document          id, tenant_id, client_id, filename, doc_type, blob_ref, ocr_text, extracted(json),
                        status(uploaded|ocr_done|matched|confirmed|needs_review), barcode, claim_id?,
                        retention_until
  └─ ChecklistItem     id, claim_id, key, label, required, satisfied_by_document_id?, status
  └─ Task(Gaps&Chase)  id, tenant_id, claim_id, kind, description, owner_user_id, status,
                        related_line_id?, client_request_sent_at?
  └─ AuditEvent        id, tenant_id, actor_user_id, action, target_type, target_id, at, detail(json)
```

★ **The designation ledger is the make-or-break correctness control.** A computed view per
`ImportEntryLine`: `available_qty → Σ designated_qty (across ALL claims) → remaining_qty` (and the same for
duty). The service layer enforces **`Σ designations ≤ available`** and **raises** on any over-designation —
extending the engine's reconciliation invariant to the persistent, cross-claim, cross-time layer. This makes
double-designation (19 U.S.C. 1313(v)) **structurally impossible**, not merely warned.

---

## 4. Tech & dependency decisions (all permissive — IP stays clean)

| Concern | Choice | License | Notes |
|---|---|---|---|
| DB (dev) | **SQLite** (`sqlite3`) | stdlib | zero-dep local run preserved; FTS5 for full-text search |
| DB (prod) | **PostgreSQL** | PostgreSQL (permissive) | driver: **pg8000** (BSD, pure-python) to avoid psycopg's LGPL flag |
| ORM / migrations | **SQLAlchemy 2.0** + **Alembic** | MIT | the standard; permissive |
| Auth | **argon2-cffi** (hash) + **PyJWT** | MIT | email/password + JWT sessions; RBAC in middleware |
| PDF→image | **pypdfium2** | Apache-2.0/BSD | permissive (Google PDFium) — **avoid** PyMuPDF (AGPL) / Poppler (GPL) |
| OCR engine | **Tesseract** via **pytesseract** | Apache-2.0 (both) | Tesseract is a **system binary invoked as a subprocess** (installed, not bundled) → no copyleft contamination |
| (optional) cloud OCR | AWS Textract / Google Document AI | commercial | **opt-in only** (paid + client data leaves → DPA + EEI review); local is the default |
| Background jobs | **arq** (Redis) or a **DB-backed job table + worker** | MIT | MVP: DB-backed worker (no extra infra); upgrade later. Use **Valkey** (BSD) if Redis is added, not Redis (SSPL) |
| XLSX report | **openpyxl** | MIT | internal expected-vs-actual report |
| PDF report | **reportlab** | BSD | branded client recovery report; or HTML→PDF |
| Frontend routing | **react-router** | MIT | adds real navigation to the existing SPA |
| Doc storage | local filesystem (dev) / S3-compatible (prod, **boto3** Apache-2.0) | — | tenant-scoped, encrypted at rest |

> **Avoid (copyleft):** Paperless-ngx (GPLv3 — inspiration, not a dependency), PyMuPDF (AGPL), Poppler/
> Ghostscript bundling (GPL/AGPL — only ever invoke as system subprocesses), psycopg (LGPL — use pg8000),
> Redis ≥7.4 (SSPL — use Valkey). Run an OSS-license scan (the `sbom.json` flow) before any release.

---

## 5. Milestones (each shippable + green; foundation first)

### M0 — Foundation & scaffolding *(no features; unblock everything)*
- Stand up `server/` with FastAPI; add SQLAlchemy + Alembic; SQLite dev DB; the `worker.py` skeleton.
- Lock the domain schema (§3) as SQLAlchemy models + the first Alembic migration.
- A `server/services/` seam that runs the existing `ingest → build_estimate → harden` and returns engine
  objects (no behavior change, just the call site moving server-side).
- **Done when:** `alembic upgrade head` builds the schema; a smoke test persists a tenant+client+program and
  round-trips an engine estimate into a Claim with Designations. Engine's 112 tests still green.

### M1 — Persistence spine + the DESIGNATION LEDGER *(the P0 correctness core)*
- Persist the full estimate: Claim + ClaimLines + Designations + ImportEntryLines + ExportLines.
- The **claim status ledger** (draft→ready→filed→under_review→liquidated→paid; estimated/defensible/actual).
- The **designation ledger** service: per-import-line `available→designated→remaining`; the
  **over-designation invariant raises** across claims and over time.
- AuditEvent logging on every state change.
- **Tests (rigor = engine-grade):** persistence round-trip; **two claims against the same import lines cannot
  over-designate** (the across-time 1313(v) test); status transitions; audit trail completeness.

### M2 — Auth & RBAC
- Users, login (argon2 + JWT), org/tenant isolation enforced at the data-access layer.
- Roles: **Admin · Preparer · Reviewer · Licensed Signer · Client (read-only)**; the existing sign-off gate
  → the **Signer** role; client role scoped to one Client.
- **Tests:** tenant isolation (no cross-tenant read); role enforcement per route; signer-only sign-off.

### M3 — Portfolio cockpit & work-queue home *(flip "calculator" → "daily tool")*
- API: claims-by-status, exception lanes, the **5-year-clock / expiring-value** rollup, per-client accrued $.
- Frontend: **react-router + auth UI**; the **work-queue home** (due / exceptions / awaiting-sign-off /
  CBP-RFI lanes); client & program management; a claim list → the existing estimate/glass-box/defensibility/
  filing views become the **claim-detail tabs**.
- **Tests:** API correctness; an in-browser pass (login → cockpit → open a claim).

### M4 — OCR document-intake *(the headline new layer)*
- Upload → tenant-scoped encrypted store → background **OCR (pypdfium2 + Tesseract)** → **classify** doc type
  (7501 / BOL / AES-EEI / invoice / 7553 / BOM) → **extract entities** (entry #, ITN, HTS, dates, duty
  amounts, parties) via per-type patterns → **propose a match** to client/program/claim/import-line/export-
  line → **human-confirm** (extracted fields land as `needs-review` until confirmed — never auto-trusted).
- **Full-text search** (FTS5) over OCR text; the **audit binder** per claim (originals + extracted data +
  links + retention clock). **Barcode/cover-sheet routing** (secondary; for physical batch scans).
- **Tests:** OCR pipeline on scanned-7501/BOL/AES fixtures; extraction accuracy thresholds; match-proposal
  correctness; the confirm flow upgrades `needs-review → confirmed`; nothing auto-files.

### M5 — Reconciliation workbench + per-type checklist + Gaps & Chase *(the workflow heart)*
- **Checklist engine:** the required/optional document & data items **reconfigure by drawback type + config**
  (substitution hides lot/serial; manufacturing demands BOM + ruling; destruction needs 7553; WPN removes it;
  OTW for retroactive). This drives the **"complete claim"** gate (190.51).
- **Reconciliation match-grid:** imports ↔ exports (or BOM/withdrawals), **UOM mismatches surfaced**, built on
  the engine's matcher + the persisted designations; reviewable/annotatable.
- **Gaps & Chase queue:** every unmet checklist item / missing ITN-proof / undocumented yield → a **task +
  owner + one-click client-request**, with a **"$X provable / $Y blocked" impact meter**.
- **Tests:** checklist reconfigures by type/config; gaps detected; complete-claim gate blocks sign-off until met.

### M6 — Configs/privileges + bond/AP + client deliverables
- **Per-program config** in CBP's vocabulary: privileges **AP / WPN / OTW**, accounting method (FIFO/LIFO —
  direct-ID only), substitution vs direct-ID, eligible tariff layers (engine already), manufacturing ruling.
  Config reconfigures the checklist, the validators, and the engine parameters.
- **Bond / AP / privilege tracking** + the **"time-to-cash" framing** (~3 weeks AP vs at liquidation);
  **OTW as a one-shot** control that quantifies the retroactive dollars it unlocks; the **two modes**
  (retroactive look-back vs periodic/accrual).
- **Client deliverables:** internal **XLSX** (program-wide, expected-vs-actual) + branded **client recovery
  report (PDF)** — the glass-box "here's exactly how your refund was built."
- **Tests:** config drives behavior end-to-end; report generation + reconciliation of report totals to the
  defensible headline.

### M7 — Lifecycle / lookup / alerts + hardening
- Claim **lifecycle tracking** (filed→liquidated→paid; AP true-up; **180-day protest** window; **3-yr
  retention** clock); **alerts/notifications** (deadlines, status changes, CBP RFI).
- **Lookup**: HTSUS / CBP-ruling (CROSS) / Schedule-B / entry.
- The **insider grid conventions** polished throughout (saved views, multi-select bulk actions, status-as-
  filter, exports from every grid).
- Full test pass; updated docs; a multi-client demo dataset; `make demo` extended to the broker flow.

---

## 6. Cross-cutting

- **Compliance evolves with the model.** Multi-tenant retention replaces "no-retention"; the `legal/` DPA +
  service-provider terms become load-bearing; encryption-at-rest + access-audit logging required once real
  client data flows; local OCR keeps EEI in-tenant by default. The flat-fee, no-contingency, licensed-filer-
  signs posture is unchanged. Update `COMPLIANCE.md` as M2/M4 land.
- **Testing bar:** engine-grade for the designation ledger and the checklist/complete-claim gate (these are
  correctness/compliance-critical); standard coverage elsewhere; an in-browser pass per frontend milestone.
- **The engine-purity rule is enforced by a test:** a lint/test asserting `engine/drawback/` imports only the
  stdlib (so the moat never acquires a dependency or a DB import).
- **Keep `sbom.json` / `THIRD-PARTY-NOTICES` current** as deps are added; OSS-license scan before release.

---

## 7. Sequencing, scope & risk

- **Order is dependency-driven:** M0→M1 (the spine) unblock everything; M3 (cockpit) makes it *feel* like a
  product; M4 (OCR) and M5 (workbench/checklist) are the differentiating daily-workflow value; M6–M7 round it
  out. Don't build features before the persistence + designation-ledger foundation.
- **Biggest risk = the designation ledger correctness** (cross-claim/cross-time double-designation). Mitigate
  with engine-grade tests and a DB-level constraint plus a service invariant that raises.
- **Second risk = OCR accuracy → claim corruption.** Mitigated structurally: OCR is `needs-review` until
  human-confirmed; the signer certifies; nothing auto-files. Local OCR first; cloud IDP opt-in.
- **Scope honesty:** this is a multi-month application build (the *engine* — the hard, novel part — is done).
  Each milestone is independently demoable, so value compounds and the sell-vs-operate decision can be made at
  any point against a working, increasingly valuable asset.

## 8. Start here
**M0 + M1** — scaffold `server/`, the schema + first migration, and the persisted designation ledger with its
across-time conservation test. That single foundation converts the calculator into a multi-claim system and
de-risks everything downstream.
