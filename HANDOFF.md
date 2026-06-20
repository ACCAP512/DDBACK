# HANDOFF — Drawback Engine

**Read this first.** One page to resume the build in a fresh session with zero context loss.
Everything below is durable in this repo (git) and in the builder's project memory — the chat history is not needed.

---

## Where we are (2026-06-20)

- **The engine is built and verified — the hard, novel part is done.** Pure-stdlib matcher (exact
  min-cost-max-flow), VERIFIED-only structurally-defensible headline, mandatory licensed-filer sign-off,
  and real-format ingestion (NetSuite × CBP 7501/ACE × AES/EEI). The 112 engine tests stay green, untouched.
- **The direction is decided:** evolve the single-claim engine into a multi-tenant **"arm-the-broker"
  drawback OS** — sell flat-fee tooling so customs brokers / in-house duty-drawback specialists keep their
  **own** portfolio (the anti-Pax / picks-and-shovels play; sell-vs-operate endgame stays open).
  Rationale: `docs/MONETIZATION.md`, `docs/UX_WORKFLOW_PLAN.md`.
- **The build is in motion:** `docs/BUILD_PLAN.md` (milestones **M0 → M7**). **M0–M3 are done — 158 tests
  green.** The `server/` app layer + the persisted **designation ledger** (across-time 1313(v) conservation),
  **auth + structural tenant isolation + RBAC**, and the **portfolio cockpit & work-queue home** (react-router
  SPA: login → cockpit → claim-detail tabs). It is now a real multi-tenant web app, not just a calculator.
  **M4 (OCR document-intake) is next.** Run `make seed && make server` → open http://localhost:8001.

---

## Resume prompt (paste into a fresh session opened in this repo)

> Read `HANDOFF.md`, `docs/BUILD_PLAN.md` (§5 M4), and `docs/COMPLIANCE.md`, then start **M4 — OCR
> document-intake**: upload → tenant-scoped encrypted store → background extraction through the pluggable
> `OcrBackend` ladder (Tier 0 text-layer via pypdfium2 → **Tier 2 cloud vision-LLM default** → Tier 1 local
> fallback for privacy-locked tenants, config per tenant) → classify → extract entities → validate →
> propose-match → **human-confirm** (`needs_review` until confirmed; nothing auto-files); FTS5 search + the
> audit binder + per-tenant page metering. Keep `engine/drawback/` and its 112 tests untouched; permissive
> deps only; record any new dep in `THIRD-PARTY-NOTICES.md`/`sbom.json`. Small commits, each ends green.

---

## Done so far (M0–M3) · the next action (M4)

- **M0–M3 are built and green (158 tests).** M0 scaffolded `server/` (FastAPI + SQLAlchemy 2.0 + Alembic,
  SQLite dev; engine imported as a library). M1 laid the domain schema + the persisted **designation ledger**
  (per import line `available → designated → remaining`, summed across **all** claims over time, raising on
  any over-designation — 1313(v) made structurally impossible). M2 added auth (argon2 + JWT), **structural
  tenant isolation** at the data layer, and RBAC (Admin/Preparer/Reviewer/**Signer**/Client). M3 built the
  **portfolio cockpit & work-queue home**: rollup domain (lanes, per-client accrued, the **5-year clock**),
  the cockpit/management/list/lifecycle API, a demo seed (`make seed`), and the **react-router SPA** (login →
  cockpit → claim-detail tabs: Overview/Glass-box/Ledger/Audit). The engine + its 112 tests are untouched.
- **The next action — M4 (OCR document-intake).** The headline new layer: the pluggable `OcrBackend` ladder
  (text-layer → cloud-VLM default → local fallback), classify → extract → validate → propose-match →
  **human-confirm**, FTS5 + the audit binder, per-tenant metering. OCR *proposes*; a human *confirms*; the
  signer *certifies* — nothing auto-files. See `docs/BUILD_PLAN.md` → §5 (M4) and the cloud-VLM-default plan
  (`git log` — "plan(M4)"). The `server/ocr/` package is a placeholder awaiting this build.

---

## Non-negotiable guardrails (already decided — do not re-litigate)

1. **Engine purity.** Nothing in `engine/drawback/` may gain a dependency. The new app *consumes* the
   engine; it never edits it. The 112 engine tests stay green throughout.
2. **Permissive deps only** (the IP must stay clean and sellable). Use: SQLAlchemy, Alembic, **pg8000**
   (not psycopg/LGPL), argon2-cffi, PyJWT, **pypdfium2 + Tesseract** (OCR), openpyxl, reportlab, **Valkey**
   (not Redis/SSPL). **Avoid all copyleft:** Paperless-ngx (GPLv3), PyMuPDF (AGPL), Poppler/Ghostscript.
   Every new dependency is recorded in `THIRD-PARTY-NOTICES.md` and `sbom.json`.
3. **Compliance posture is load-bearing and unchanged.** Estimate-not-promise framing; **flat-fee, never
   contingency**; the **licensed-filer sign-off gate stays mandatory** before any claim is final;
   **OCR proposes → human confirms (`needs-review`) → licensed signer certifies — nothing auto-files.**
   The tariff-eligibility config is **date-stamped 2026-06-19** and must be re-verified before real use.
4. **Data posture shift (new in this build).** The broker *retains their book of business*, so auth,
   multi-tenant isolation, encryption, and retention come **in scope** — the `legal/` DPA + tenant
   isolation become load-bearing. Local OCR keeps client documents (EEI) in-tenant by default; cloud IDP
   (Textract/Document AI) is opt-in only, because it sends client docs out.
5. **Small commits; keep the tracking docs current** (`docs/PROGRESS.md`, `docs/LIMITATIONS.md`). That
   discipline is exactly what makes this build resumable across context boundaries.

---

## Orientation map

| Need | Where |
|---|---|
| **What to build next** | `docs/BUILD_PLAN.md` → §8 "Start here" |
| Why — insider daily-workflow research | `docs/UX_WORKFLOW_PLAN.md` |
| Legal guardrails (sign-off, flat-fee, EEI, IP) | `docs/COMPLIANCE.md` |
| Monetization strategy | `docs/MONETIZATION.md` |
| Legal rules + citations | `docs/RESEARCH.md`, `docs/ASSUMPTIONS.md` (A-01..A-23) |
| What's done + honest gaps | `docs/PROGRESS.md`, `docs/LIMITATIONS.md` |
| The engine (don't rebuild it) | `engine/drawback/` |

---

## Verify the baseline before building

```bash
cd ~/Desktop/drawback-engine
make test     # 158 green — engine (112) + broker-OS app layer (46)
make demo     # real-format ingest → estimate → defensibility → signed claim (engine CLI)
make migrate  # build the broker-OS schema (alembic upgrade head)
make seed     # reset + seed a demo broker book-of-business into the dev DB (M3 cockpit)
make server   # serve the broker-OS API + SPA at http://localhost:8001
              #   sign in: admin@northstar.test / signer@northstar.test / client@northstar.test  (pw: drawback)
```

If `make test` is green, the foundation you're building on is sound. Then start **M4**.
