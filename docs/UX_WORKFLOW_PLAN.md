# UX_WORKFLOW_PLAN.md — making it "built by an insider"

**Date:** 2026-06-19 · **Status:** research synthesis + prioritized UX plan (NO execution). Synthesizes four
primary-source research streams (the drawback specialist's daily workflow & pain points; document intake &
data-prep reality; features pros expect + competitor/analog UX; the practitioner's insider vocabulary &
audit mental model). Authoritative sources: 19 CFR Part 190 / 19 U.S.C. 1313, CBP drawback guidance & CSMS,
drawback-firm process pages (Charter, J.M. Rodgers, Comstock & Holt, Alliance, Tradewin, STARUSA), the AI
entrants (Pax AI, Zollback, Tariff Refund HQ), incumbent software (Descartes, ONESOURCE, MIC, CargoWise),
job postings, and G2/Capterra reviews. Full URLs in the four research transcripts.

> **The one-line conclusion:** the engine is excellent, but it's a **single-claim calculator**, and the
> specialist's day is **portfolio management + data wrangling + designation defense + audit-proofing**. The
> redesign is to evolve it into a **drawback book-of-business manager** — a work-queue cockpit on top, a
> forgiving intake + reconciliation workbench underneath, a persistent **designation ledger** as the spine,
> and a permanent **audit binder** behind every number. The estimate/sign-off/CATAIR engine becomes the
> *output* of that workflow rather than the whole app.

---

## 1. Who the user is, and their day

**The user** is a duty-drawback specialist / licensed customs broker — at a specialist firm (Charter, J.M.
Rodgers, Comstock, Alliance), a brokerage's drawback desk, a 3PL, or an importer's trade-compliance team.
Their toolchain today is **ACE (in) → Excel (the workbench, by default not preference) → ABI/drawback
filing system (out)**. They manage a **portfolio: many clients × many programs (unused / manufacturing /
rejected) × thousands of import lines × a rolling 5-year clock.** The week is part production (build
claims), part client service ("where's my money?"), part CBP back-and-forth.

**A representative week:** Mon — refresh ACE data, review liquidation/payment status across the portfolio;
Tue–Thu — data prep + matching for whichever client's monthly/quarterly claim is due, plus chasing missing
export docs; Fri — assemble & file the due claim(s), update clients, log records for audit. Month/quarter-end
spike as accrual claims come due across clients at once.

## 2. The workflow, where the time goes, and the pain (ranked)

End-to-end: feasibility/ROI → privilege setup (AP/WPN/OTW) → data collection → **data prep/
normalization/reconciliation** → matching/eligibility → claim assembly → file (Entry Type 47 in ACE) →
liquidation/payment tracking + AP true-up → recordkeeping/audit defense → ongoing/accrual claims.

**Ranked pain points (impact × frequency):**
1. **Fragmented, dirty data → manual normalization/reconciliation** — *the* #1 time-sink ("the biggest
   challenge to any drawback program is data processing — cleansing, manipulation, validation"). Imports are
   clean; **exports are scattered** ("TMS platforms, spreadsheets, emails, or not at all").
2. **Chasing export proof you never controlled** — missing **ITNs/BOLs** ("a leading cause of claim
   rejection"); the ex-works "who's the exporter of record?" ambiguity.
3. **Manual matching of imports↔exports** — "one of the hardest parts"; why every firm sells proprietary
   matching software.
4. **Audit anxiety — "one missing document kills the claim"** — the most *severe* impact; non-compliance →
   clawback **+ penalties** (19 U.S.C. 1593a); records must survive **3 years from liquidation**.
5. **Proving the math to a skeptical client or CBP auditor** — methodologies *do* get denied (e.g., Chicago
   Drawback Office FIFO denials).
6. **Tracking dozens of claims / liquidations / payments** across timelines + AP true-ups.
7. **The long payout wait & cash framing** — standard liquidation ~314 days; AP ~3 weeks but needs a bond +
   privileges that take 3–6 months to obtain.
8. **The silent 5-year clock** — every import line ages toward permanent forfeiture.

## 3. The practitioner's mental model (so the UX speaks their language)

- **Three separate axes — never collapsed:** **Am I eligible?** / **How much?** (99% × lesser-of) / **How
  fast + what notice?** (the privileges). Putting "time to cash: ~3 weeks (AP held)" next to the number reads
  as insider.
- **Designation is the core verb:** you don't get the duty on the export — you get back the duty on the
  **import you designate** against it, tracked in a **drawback ledger**, never claimed twice (1313(v)).
- **Two operating modes:** the one-time **retroactive 5-year look-back** (the big Year-1 claim, gated by the
  one-shot **OTW**) and recurring **periodic/accrual** claims (the go-forward annuity).
- **Calendar discipline:** the **5-year import-aging** clock, **AP→liquidation**, **1-year deemed
  liquidation**, **180-day protest** window, **3-year retention** clock are all first-class.
- **Vocabulary that must appear** (and dead-but-spoken terms to bridge): **AP / WPN / OTW**, **Entry Type
  47**, **CATAIR**, **7501 / 7553**, **AES ITN**, **designation**, **lesser-of**, **complete claim**,
  **deemed liquidation**, **protest**, **CSMS**, the **Center/CEE** & **Drawback Specialist**; bridge
  **Certificate of Delivery/CMD**, **"commercially interchangeable,"** **Part 191** → the modern rule
  ("transfer = business records under 190.10"; "j(2) substitution = the 8-digit-HTS test").

---

## 4. The core reframe: calculator → book-of-business manager

| Today (single-claim calculator) | Insider daily tool (book-of-business manager) |
|---|---|
| Load data → see one estimate → one claim | **Work queue / portfolio cockpit** across clients & programs |
| `claim → line` data model | **`portfolio → client/program → claim → line`** with persistent ledgers |
| Estimate is the product | Estimate is the *output* of an ingest→reconcile→designate→file→track workflow |
| No memory between sessions | **Claim status ledger** + **designation ledger** (running balances) |
| Per-claim recompute | Persistent **available → designated → remaining** duty per import line |
| One sign-off gate | **RBAC** (preparer → reviewer → licensed signer → client read-only) |
| Ingest to compute | **Audit binder**: retain docs + retention clock + produce-on-request package |

---

## 5. Gap analysis

### Keep central — the product is AHEAD of every product researched (do NOT dilute)
- **Glass-box per-line audit trace** — no incumbent exposes a per-dollar, rule-cited, VERIFIED-tagged trace.
- **Structurally-defensible VERIFIED-only headline** — a credible *insider* counter to the AI entrants'
  "+15% more refunds" (an audit-risk posture). "Defensible / audit-ready / defensible-on-protest" is the
  language of the job.
- **Instant self-serve estimate**, **mandatory licensed-filer sign-off** (validated — every AI entrant keeps
  a human in the loop), **real-format ingestion** (beats most on intake fidelity), **reconciliation invariant**.

### Missing — mapped to your asks + what the research surfaced
| Need | Priority | In your list? |
|---|---|---|
| **Designation ledger** (available→designated→remaining per import line; anti-double-claim across claims/time) | **P0 — make-or-break** | implied by "history" — but it's *the* correctness control |
| **Claim status ledger / history of filings** (draft→filed→under CBP review→liquidated→paid; expected vs actual) | **P0** | ✅ "history of filings" |
| **Client & program objects** + the **work-queue home** | **P0/P1** | ✅ "multi-user" / new |
| **5-year-clock / expiring-value dashboard** | **P1** | new (high insider signal) |
| **Reconciliation match-grid** + **"Gaps & Chase" queue** (missing ITN/proof/yield → tasks + client request) | **P1** | new (attacks pains #1–3) |
| **Per-client/program configs** (privileges AP/WPN/OTW, accounting method, substitution/direct-ID, eligible layers, mfg ruling) | **P2** | ✅ "custom configs" |
| **Bond / AP / privilege tracking** + "time-to-cash" framing | **P2** | new |
| **Audit binder** (record chain + retention clock + produce-on-request package) | **P2** | new (attacks the *most severe* pain #4) |
| **Client deliverables**: XLSX (internal, expected-vs-actual) + branded **client recovery report (PDF)** + the trace as "how your refund was built" | **P2** | ✅ "report xlsx/pdf for client" |
| **Multi-user RBAC + review workflow** (extends the sign-off gate) | **P3** | ✅ "multi-user" |
| **HTSUS / CROSS-ruling / Schedule-B / entry lookup** | **P3** | ✅ "lookup ability" |
| **Lifecycle tracking + alerts** (AP→liquidation→protest window→retention; deadline & CBP-RFI alerts) | **P3** | new |

---

## 6. The prioritized UX roadmap

**Sequencing principle:** items in P0–P1 convert "calculator → daily tool"; the glass-box engine already in
place becomes the thing that makes it *trusted*. Build the data-model spine before new surface features.

### P0 — The data-model spine (make-or-break; do first)
- **Objects:** `Portfolio → Client → Program → Claim → Line`. (A Program = one client's drawback type +
  config; a Claim = one filing period/batch.)
- **Claim status ledger:** persist each claim through *draft → ready → filed → under CBP review → liquidated
  → paid*, with **expected vs actual** refund. (Borrow Zollback's stage taxonomy near-verbatim.)
- **Designation ledger (the spine):** a persistent **available → designated → remaining** duty balance *per
  import entry line*, so the same duty is **structurally impossible** to designate twice across claims or
  over time (1313(v)). Wire the existing reconciliation-invariant rigor into it. *Without this, a multi-claim
  tool will eventually double-designate and create the exact penalty exposure the product exists to prevent.*

### P1 — The cockpit + the workbench (flip "open to price a deal" → "live in it")
- **Work-queue home** (replaces the "Load data" hero): lanes for *claims due this month*, *exceptions to
  clear*, *awaiting sign-off* (extends the existing gate), *CBP RFI open*. Each row actionable.
- **Portfolio cockpit:** per client — accrued recoverable $, next filing due (monthly/quarterly), pipeline
  by status, AP true-up deltas.
- **5-year-clock / expiring-value dashboard:** import lines aging toward the wall, with at-risk $ and dates.
- **Intake & reconciliation workbench:**
  - **Type-driven document checklist** — the essential-vs-optional rows *change the moment the user picks the
    drawback type* (substitution hides lot/serial tracing; direct-ID & manufacturing reveal it). Strongest
    single "insider" tell.
  - **Two-world ingest:** confident bulk path for (clean) imports (7501/ACE); **forgiving, gap-tolerant**
    path for (scattered) exports, treating a missing **ITN** as a named first-class blocker, not a null.
  - **Two-sided reconciliation match-grid:** imports ↔ exports (or BOM/withdrawals), joined by part #,
    **8-digit HTS**, or manufacturing record, reconciling **quantity, value, timing, identity**; surface
    **UOM mismatches** (HTS units vs commercial units) explicitly.
  - **"Gaps & Chase" queue** (headline feature, not an error log): every missing ITN/proof/yield/entry →
    a **task with an owner + one-click client request**, with a **claim-value impact meter** ("$X provable
    now / $Y blocked on gaps").

### P2 — Configs, privileges, audit binder, client deliverables
- **Per-client/program config** in CBP's own vocabulary: privileges (**AP / WPN / OTW**), accounting method
  (FIFO/LIFO/low-to-high — *direct-ID only*), substitution vs direct-ID, eligible tariff layers (already
  nailed), **manufacturing ruling** (general vs specific). The config reconfigures the checklist & validators.
- **Bond / AP / privilege tracking** + a **"time-to-cash" framing** on the number (~3 weeks AP vs at
  liquidation); **OTW as a one-shot, high-stakes toggle** that quantifies the retroactive dollars it unlocks.
- **Two operating modes** made explicit: retroactive 5-yr look-back vs periodic/accrual go-forward.
- **Audit binder** per claim: the complete record chain (import 7501 ↔ export proof ↔ BOM ↔ the link), a
  **retention clock to 3 years post-liquidation**, and a one-click **produce-on-request CBP package**. This
  is the feature most likely to make a licensed broker say "built by someone who's been audited."
- **Client deliverables:** internal **XLSX** (program-wide, expected-vs-actual) + a branded **client recovery
  report (PDF)**; turn the glass-box trace into the client-facing "here's exactly how your refund was built."

### P3 — RBAC, lookup, lifecycle/alerts
- **Multi-user RBAC + review workflow:** preparer → reviewer → **licensed signer** → **client read-only**;
  tasks/notifications. (The sign-off gate is the foundation to extend.)
- **Lookup:** inline HTSUS / **CROSS ruling** / Schedule-B / entry lookup while building & validating.
- **Lifecycle tracking + alerts:** AP→liquidation→**180-day protest window**→retention; deadline & CBP-RFI
  alerts (email/webhook). Preserve the full computation rationale to support a **protest**.

### Cross-cutting — the grid conventions that signal "insider" (apply throughout)
Dense, **keyboard-navigable data grids**; **multi-select + bulk actions** ("search entries → select many →
add to claim", per CargoWise's pattern); **saved per-user views**; **status-as-a-filter**; **exports from
every grid**; audit trail as a feature, not a log. This is the cheapest, highest-signal "pro vs consumer"
differentiator.

---

## 7. Pre-flight checklist as a first-class screen (the audit-defensive finale)
Render the practitioner's pre-flight as a literal green/blocked checklist before sign-off (it *is* the value
prop to a specialist): correct provision + matching lesser-of comparator; 8-digit (or "other"→10-digit)
substitution; 190.14 method on direct-ID only; manufacturing ruling in place; eligible-charges-only (232/
AD-CVD/IEEPA/122 excluded & labeled); 99% applied; each designation within the 5-year window; **7553 filed in
time OR WPN held OR OTW spent**; AP bond sufficient; complete-claim test (claim + 7553/waiver + export/
destruction evidence); reconciliation invariant holds; **headline rests only on VERIFIED + proof-backed
lines**; licensed-filer certifies; package retained & producible 3 yrs from liquidation.

## 8. What NOT to lose
The glass box, the VERIFIED-only defensible headline, the instant estimate, the licensed-filer sign-off, the
real-format ingestion, and the reconciliation invariant are the moat — *more rigorous than anything in the
market.* The new portfolio/ledger/queue/binder shell exists to make these strengths usable **daily**, not to
replace them. The competitor field's two biggest complaints are **complexity/learning curve** (CargoWise) and
**price** (Descartes) — a focused, transparent, glass-box drawback tool with the workflow spine is positioned
squarely in that gap.

## 9. Sources
Workflow/pain: drawback-specialist job postings (Indeed/LinkedIn/ZipRecruiter/Manpower), BDO, Tradewin,
STARUSA, Caspian, Flexport, Comstock (`dutydrawback.com`), J.M. Rodgers, CBP "Drawback in ACE", CSMS
#19-000197. Intake/data: 19 CFR 190.10/190.35/190.72, 15 CFR 30.6, CBP 7501/7553, freehand.ai, lightsource,
firm "getting started" pages. Features/competitors: Descartes, ONESOURCE/Oracle GTM, MIC-CUST, CargoWise,
Pax AI, Zollback, Tariff Refund HQ; G2/Capterra/TrustRadius. Insider/audit: 19 U.S.C. 1313/1508/1514/1593a,
19 CFR Part 190 (190.2/7/8/10/14/36/51/91/92, Subparts I & S), CBP CSMS #49358330 (CEE), Neville Peterson,
Diaz Trade Law. (Consistent with the engine's existing `docs/RESEARCH.md` + `docs/ASSUMPTIONS.md`.)
