# HANDOFF — Drawback Engine

**Read this first.** One page to resume the build in a fresh session with zero context loss.
Everything below is durable in this repo (git) and in the builder's project memory — the chat history is not needed.

---

## Where we are (2026-06-19)

- **The engine is built and verified — the hard, novel part is done.** Pure-stdlib matcher (exact
  min-cost-max-flow), VERIFIED-only structurally-defensible headline, mandatory licensed-filer sign-off,
  and real-format ingestion (NetSuite × CBP 7501/ACE × AES/EEI). **112 tests green**, verified in-browser.
- **The direction is decided:** evolve the single-claim engine into a multi-tenant **"arm-the-broker"
  drawback OS** — sell flat-fee tooling so customs brokers / in-house duty-drawback specialists keep their
  **own** portfolio (the anti-Pax / picks-and-shovels play; sell-vs-operate endgame stays open).
  Rationale: `docs/MONETIZATION.md`, `docs/UX_WORKFLOW_PLAN.md`.
- **The build plan is written:** `docs/BUILD_PLAN.md` (milestones **M0 → M7**). We are **about to start
  M0 + M1**. None of the new application layer is built yet — this is the clean starting line.

---

## Resume prompt (paste into a fresh session opened in this repo)

> Read `HANDOFF.md`, `docs/BUILD_PLAN.md`, and `docs/COMPLIANCE.md`, then start **M0 + M1**: scaffold the
> new `server/` layer (FastAPI + SQLAlchemy, SQLite dev → Postgres, permissive deps only, engine stays
> pure-stdlib), lay down the domain schema + first Alembic migration, and build the **persisted designation
> ledger with its across-time anti-double-claim (19 U.S.C. 1313(v)) conservation test**. Keep
> `engine/drawback/` and its 112 tests untouched. Small commits.

---

## The next action — M0 + M1 (the foundation)

- **M0 — scaffold.** New `server/` package: `db · domain · auth · ocr · workflow · reports · services ·
  api · worker.py`. FastAPI app; SQLAlchemy 2.0 + Alembic; SQLite for dev. The engine is untouched and
  imported as a library.
- **M1 — persistence + the make-or-break control.** The domain schema —
  `Tenant → User → Client → Program → Claim → ClaimLine`, plus `ImportEntryLine`, `ExportLine`,
  **`Designation`** (★ the ledger), `Document`, `ChecklistItem`, `Task`, `AuditEvent` — with the first
  migration, **and the persisted designation ledger**: per import line `available → designated → remaining`
  duty, summed across **all** claims over time, with an invariant that **raises** on any over-designation.
  Build it to engine-grade test rigor (including an across-time conservation test). This is the single
  thing a multi-claim tool must get right — it makes double-designation structurally impossible (1313(v)).
  See `docs/BUILD_PLAN.md` → §8 "Start here."

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
make test     # 112 green — the engine's correctness suite
make demo     # real-format ingest → estimate → defensibility → signed claim
make run      # serve API + SPA at http://localhost:8000
```

If `make test` is green, the foundation you're building on is sound. Then start **M0**.
