# LIMITATIONS.md — assumptions, stubs, and known gaps (honest inventory)

Per PRD §10/§11, this is the complete, honest list of what is assumed, stubbed, or not yet built. Nothing
here is hidden in the UI; the app marks every simulated seam and every conservative exclusion.

## 1. This is decision-support, not a filer of record (by design)
- The engine **prepares, computes, and formats**; it does **not** certify or transmit a claim and is **not**
  legal advice (19 CFR 190.6; ASSUMPTION A-17). A licensed customs broker/attorney or the claimant's
  authorized signer must certify and file via ACE/ABI. The UI and README state this plainly.
- **Compliance posture (see [`COMPLIANCE.md`](COMPLIANCE.md)).** The team is unlicensed; the lawful path is
  to **sell/flat-fee-license** the software (CBP HQ H350722, Jan 2026) — operating it as a service would be
  unlicensed customs business. Enforced in code/docs: a **mandatory licensed-filer sign-off gate**
  (`filing/signoff.py`; `submit` 428s until a lawful operator attests) and an estimate-not-promise posture.
  A customs/privacy attorney must finalize the EULA/DPA (drafts in `legal/`) before real use.
- **Correctness hardening (`defensibility.py`).** A **structurally-guaranteed defensible headline** rests
  ONLY on [VERIFIED] legal rules; a **reconciliation invariant raises** on any 99%/lesser-of/claimed-≤-duty
  violation; a per-claim **defensibility report** lets a customs professional validate from the trace alone.
  This is a *post-hoc validator over public output* — it does not change the matcher's computed numbers.

## 2. Legal-scope limitations (what the engine does and does not compute)
- **Drawback types:** fully built = **unused merchandise, §1313(j)(1) direct-ID and (j)(2) substitution**
  (the primary persona's re-export case and the cleanest linkage problem). **Manufacturing (a)/(b)** rules
  and the distinct lesser-of comparator (A-05) are encoded and the provision codes exist, but **BOM-based
  manufacturing matching is partial/stubbed** — the engine does not yet consume bills of materials to link
  imported inputs to exported finished goods. **Rejected merchandise (c)** is represented as a type only.
  **Petroleum §1313(p)** and **sought-chemical-elements §1313(b)(4)** are explicitly out of scope (their
  special matching rules would be wrong if (j)(2) logic were reused).
- **Retroactive substitution** (exported substitute *before* the designated import, within the window) is
  **conservatively excluded** — the engine requires export ≥ import (A-09). This under-claims rather than
  over-claims; some legitimate recovery is moved to "blocked/needs review."
- **The §1313(r) major-disaster / CBP-fault filing extension** is not granted (A-09): the 5-year window is
  enforced strictly.
- **The comparator (lesser-of prong ii)** is computed at the export HTS's eligible-charge rate profile
  (A-21), a standard but **[INFERRED]** computation. Its uncertainty (would the substituted good really
  bear Section 301?) is expressed honestly through the **headline range** — the low end excludes speculative
  301 (A-22) — not by inflating the point estimate.
- **Excise double-drawback cap** (19 CFR 190.22(a)(1)(ii)(C)/190.32(b)(3)) is **not applied** because it was
  judicially invalidated (*NAM v. Treasury*, Fed. Cir. 2021; A-07). This *raises* excise recovery vs. the
  literal (dead) reg; flagged in the trace. Excise is a minor charge for the electronics persona, so this
  path is lightly exercised.
- **Per-unit MPF/HMF** are modeled as flat ad-valorem rates; real MPF has a per-entry min/max cap that
  per-unit averaging only approximates. The effect on totals is small.

## 3. Date-sensitivity (the fastest-moving risk)
- **Tariff-layer eligibility is stamped as-of 2026-06-19** and centralized in
  `engine/drawback/config/tariff_eligibility.py`. It encodes: Section 301 / MPF / HMF / base duty / importation
  excise **eligible**; Section 232 / IEEPA / Section 122 / AD-CVD **excluded** (A-12/A-13). These are litigated
  and change fast. **Re-verify current CSMS messages and the CIT/Fed. Cir. dockets before any real use.** The
  UI surfaces the as-of date and the eligible/excluded table.
- **IEEPA** is treated as struck-down and routed to a separate, clearly-labeled **CAPE** track — never added
  to a drawback total. If IEEPA's status changes, update the config.
- **Pre-2004 HMF non-eligibility** (HMF only became drawback-eligible via the 2004 amendment) is noted in the
  config but not modeled — all synthetic data is current-era.

## 4. Data limitations
- **HTS reference is a local fixture** (`data/hts_reference.py`), not a licensed/maintained HTSUS dataset —
  ~50 curated codes covering the electronics persona plus deliberate "other"-basket cases. Unknown codes get
  0 base/301 rates and are flagged by the parser as a data-quality warning. **Seam:** swap in a real HTSUS
  reference behind the same interface and the rules/matcher are unchanged.
- **All bundled data is synthetic** (`data/generator.py` and the ingest demo `samples/demo_netsuite` +
  `samples/demo_customs`), clearly labelled and isolated from any real path. It is **real-format** (the
  field names/layouts are real — CBP 7501/ACE, AES/EEI per 15 CFR 30.6, NetSuite saved-search ids) but the
  **values are synthetic and illustrative**; the dollar magnitudes are not a real importer's.
- **Liquidation status** is taken from the data (A-14); the engine cannot independently verify finality.
  Not-liquidated imports are excluded from the headline and surfaced as potential.
- **Ingestion (`drawback/ingest/`):** a real-format layer now joins a **NetSuite commercial spine** to a
  **CBP 7501/ACE + AES/EEI customs overlay** → the engine's input contract, with quantity reconciliation,
  multi-receipt-to-one-entry, and AES export-proof matching. Every NetSuite/customs→drawback mapping is
  tagged `[VERIFIED]/[INFERRED]/[GUESS]` in [`INGESTION.md`](INGESTION.md). **Not built / future adapters:**
  scanned-PDF OCR (deliberately out of scope — structured files only), the full long tail of per-broker
  column header variants (a small alias layer is included), and ERP systems other than NetSuite. Real broker
  files vary; expect a per-tenant column-mapping step before production.

## 5. Stubbed (designed, not live) — external blockers
- **CBP/ACE/ABI transmission:** there is no filer code, broker license, or ACE access in this build. Layer 3
  produces a **CATAIR-shaped** claim object + a record-typed transmission rendering and a **mock submit** that
  writes to `filing_out/` and validates structure. It is **not** the exact 80-char fixed-width wire format and
  transmits nothing. Marked "SIMULATED" in code and UI (D-009).
- **Claim lifecycle / status dashboard:** runs on **simulated** status data behind a clean interface
  (`filing/lifecycle.py`). Projected dates illustrate AP vs. liquidation timing; they are not real CBP events.
- **The licensed-filer / audit-defense human workflow** is represented in the lifecycle and UX but not faked;
  the **sign-off gate** (`filing/signoff.py`) records a real attestation structure but does not verify a
  broker's license against any registry — that check belongs to the operating broker/importer.
- **Live NetSuite access:** the ingestion layer ships a `StubbedNetSuiteClient` marked "NOT CONNECTED —
  fixture mode" reading the demo fixtures. The live **SuiteQL / SuiteTalk REST** client (OAuth/TBA) is the
  documented seam (`ingest/client.py`), not implemented — no live credentials in this build.

## 6. Engine performance & scaling
- The matcher decomposes per **8-digit HTS bucket** and runs an exact min-cost-max-flow per bucket. Concrete
  tested target: a realistic mid-market dataset (~1,200 import lines + exports across ~50 subheadings)
  estimates in **< 5 s**; ~4,000 import lines complete well under the test ceiling. Real importers carry
  **hundreds** of distinct subheadings, which keeps buckets small.
- **Scaling seam:** a pathological dataset with very few distinct HTS codes but huge line counts produces a few
  enormous buckets where per-bucket MCMF gets slow (the synthetic generator's limited vocabulary is a worst
  case). A windowed-transportation fast-path (sorted-merge greedy when the bucket has no time-window
  fragmentation, falling back to MCMF) is the documented future optimization. The engine logs which path runs;
  no coverage is silently capped.
- **Fractional units of measure** are not modeled — quantities are integer HTSUS units (A-16). Fractional-UOM
  support would scale quantities to integers; documented seam.

## 7. Out of scope (PRD §7) — intentionally not built
Product naming/branding, payments/billing, authentication/multi-tenant hardening, production deployment,
and anything requiring a customs broker license. Noted as future work.

## 8. Where research could not fully verify (carried from RESEARCH.md)
- `ecfr.gov` and `cbp.gov` blocked automated fetch during Phase 0; CFR text came from the Cornell LII / GovInfo
  primary mirrors and CBP positions from CSMS numbers + the CATAIR + statute/regs. A human spot-check against
  live eCFR and current CSMS is advised before production use.
- The exact byte-level CATAIR record layout and the §1313(r) major-disaster extension text were not
  verbatim-confirmed; the engine uses the conservative default and a record-typed (not wire-exact) claim file.
- Market-size priors ("$15B unclaimed", "80% never file", "Charter = 1/3") are **unsourced vendor marketing**
  and are **not** presented as fact anywhere; the sourced figure (drawback paid ≈ $1B FY2019 → ~$3.9B FY2023)
  frames the docs instead.

## 9. Broker-OS application layer (M0–M3 built; M4–M7 not yet)
The `server/` + `web/src/broker/` multi-tenant app brings auth/multi-tenancy **in scope** (superseding §7's
single-claim-engine "out of scope" note) — see `docs/BUILD_PLAN.md`. Built and tested: M0 scaffold, M1
persistence + the **designation ledger** (across-time 1313(v) conservation), M2 auth + structural tenant
isolation + RBAC, **M3 portfolio cockpit + work-queue home** (this milestone). Not yet built: **M4** OCR
document-intake, **M5** reconciliation workbench + checklist + Gaps&Chase, **M6** configs/privileges + bond/AP
+ client deliverables, **M7** lifecycle/lookup/alerts + hardening. Specific M3-era gaps:
- **5-year-clock scaling.** The expiring-value rollup (`server/domain/clock.py`) is *precise* (it reuses the
  engine's dated eligibility config) but computes the eligible-duty-at-risk with a **Python pass over the
  tenant's import lines** — streamed for bounded memory, yet O(import lines) CPU per cockpit load. At the
  RESEARCH-sized book (10⁵–10⁷ lines) the documented optimization is to **denormalize an `eligible_duty`
  column** at upsert time → a pure SQL/materialized rollup (or a cached summary). Correct today; not yet
  optimized for the largest books. No coverage is silently capped.
- **Lifecycle controls are minimal.** `POST /claims/{id}/transition` walks the M1 status ledger with a
  file-needs-sign-off gate (428); the richer lifecycle (180-day protest clock, AP true-up workflow, RFI
  handling, retention timer) is M7. CBP liquidation/payment figures are entered by staff (no ACE feed).
- **Client portal is partial.** The `client` role is read-only and row-scoped to its one importer at the
  data layer (verified), and lands on its own claims; a polished standalone client portal is later work.
- **Login is single-tenant-per-email** (carried from M2): if one email exists in two tenants, login is
  rejected rather than disambiguated — a production org-selector is a documented follow-up.
- **Claim-detail trace rendering** uses a JSON view of the engine's glass-box trace; reusing the demo SPA's
  richer `TraceDrawer` (numbered derivation, live citation links) against the persisted designation is a
  deferred polish item.
- **Engine purity preserved.** The app consumes the engine one-way (a test asserts `engine/drawback/` stays
  stdlib-only); none of M0–M3 modified the engine or its 112 tests.
