# Go-To-First-Customer Plan

**The one job of this phase:** land **one design partner**, get **one real, defensible, fileable drawback
claim** out of the tool on *their own data*, and convert it into the **first paying logo**. That single
logo — not any code sale — is what creates leverage, removes the acquirer's "we'll just build it" option,
and starts the only flywheel that leads to real money (see `docs/MONETIZATION.md`).

This plan is grounded in the market research: a ~9,000-lifetime-claimant niche dominated by a few
specialists who build in-house, with a long tail the specialists underserve. We win the tail.

---

## 1. The ideal first customer (ICP)

**A mid-market distributor or brand of *dutiable consumer goods* that imports on high duty, re-exports or
destroys a recurring chunk, and currently either isn't claiming or pays a specialist a 20–30% contingency.**

Concrete profile:

| Trait | Target | Why it matters |
|---|---|---|
| **Product** | Apparel, footwear, consumer electronics, housewares, auto parts, sporting goods | High duty rates + lots of **Section 301 (China 25%)** exposure = big eligible duties. The engine treats Section 301 as eligible (A-21). |
| **Drawback type** | **Unused-merchandise** — imports goods, re-exports or destroys them substantially unused (or substitutes interchangeable goods) | This is what the MVP *fully* builds (§1313(j)(1)/(j)(2)). **Avoid** manufacturing-drawback-heavy prospects — BOM matching is only partial (`docs/LIMITATIONS.md`). |
| **Flows** | Imports dutiable goods **and** exports a recurring 10–30% (to Canada/Mexico/LatAm/affiliates) or destroys obsolete/returned inventory | Drawback only exists where there's *both* duty paid *and* later export/destruction. Recurring = recurring SaaS. |
| **Size** | ~$50M–$500M revenue | Big enough that the refund is worth real money; small enough to **lack in-house drawback software/staff** (those go to Charter/J.M. Rodgers). |
| **Data** | On a modern ERP — **NetSuite** ideal, SAP/QAD fine — with ACE access | The ingest layer is built for **NetSuite × CBP 7501/ACE × AES/EEI**. A NetSuite shop is a plug-in fit. |
| **Status quo** | Pays a specialist **20–30% contingency**, or **isn't claiming at all** ("we know we leave money on the table") | Both are easy ROI conversations. The non-claimers are the softest target — no incumbent to displace. |

### Who actually signs & transmits (the compliance reality)
The tool **prepares and maximizes**; a **licensed party signs and transmits** via ACE/ABI. Two clean
structures — qualify which one the prospect fits:

- **(A) Self-filing importer** with its own ACE/ABI filer (or self-filing its own account, 19 CFR 111.2
  exemption): their licensed person is the signer in the sign-off gate. Cleanest — no third party.
- **(B) Importer + their existing broker:** importer uses the tool to prepare the defensible claim, hands
  the finished package to their broker to review, sign, and transmit. The **broker is the signer**. Most
  importers already have a broker, so this is the common case — and it makes the broker an ally, not a
  competitor.

Either way **you remain a software vendor** (flat fee, never contingency) — the lawful posture per
CBP HQ H350722 (`docs/COMPLIANCE.md`).

### Anti-targets (do not chase)
- **Petroleum / chemicals** — Charter Brokerage (Berkshire-owned) dominates; don't fight there.
- **Fortune 500 / anyone with in-house drawback** — they have J.M. Rodgers or their own engine; they'll never buy.
- **Manufacturing-drawback-dependent** importers — wait until BOM matching is built.

---

## 2. Where to find them (with $0 budget)

1. **Trade-data reverse-search (the precise way).** Importer-of-record data is semi-public
   (ImportGenius / Panjiva / free CBP & Census trade tools). Build a list of companies importing
   **high-duty Section 301 goods from China** *and* showing export activity (or known re-exporters /
   destroyers). 50–100 names fitting the ICP is a weekend of list-building.
2. **The broker channel (the fast way).** One mid-tier customs broker carries 30–50 importer clients.
   Partnering with a single broker gets you (a) the licensed **signer** you lack, (b) their **book of
   clients**, and (c) credibility. Pitch: *"Pax owns the client and disintermediates you; we let you keep
   your portfolio and just hand you better tooling for a flat fee."*
3. **Warm/affinity routes.** Trade-compliance LinkedIn groups, NCBFAA member brokers, apparel/footwear/
   electronics trade associations, drawback-specific forums. Tariff turmoil has importers actively *looking*
   for drawback right now — the tide is in.

**Who to contact at the company:** the **trade-compliance / customs manager** or **director of logistics/
supply chain** is the champion (feels the pain); the **CFO/controller** is the budget-holder (drawback =
found money — CFOs love it). Lead with the champion, arm them to sell finance internally.

---

## 3. The pitch

**One-liner:** *"See your defensible duty-drawback number in minutes from data you already have — and keep
the 20–30% you'd hand a specialist, with a glass-box audit trail your broker and CBP can trace dollar-for-
dollar."*

**The ROI math (make it concrete on their numbers):**
> Import $20M/yr of Section 301 goods at 25% = **$5M duties paid**. Re-export 15% unused = **$750K eligible
> duties → ~$500K realistic refund** after windows & the lesser-of rule. A specialist takes 25% = **$125K**.
> Our flat fee is a small fraction of that — and if you're *not* claiming today, the entire $500K is net new.

**Why us, not the specialist / not building it:**
- **Instant & glass-box** — no 6-week "assessment," no black box. Every claimed dollar traces to the import,
  the export, the rule, and a confidence level.
- **Defensible by design** — the headline rests only on **[VERIFIED]** legal rules; it **reconciles**; a
  **licensed filer signs off** before anything is final. Built for an audit, not just an estimate.
- **You keep control** — you (or your broker) stay the filer of record. We're software, not a service that
  owns your refund.
- **Flat fee** — predictable, not a tax on your own money.

**The demo flow (the "wow"):** load *their* NetSuite + ACE/7501 export → instant estimate leading with the
**audit-defensible** figure → drill any import↔export pair in **Glass Box** → validate in **Defensibility**
(reconciliation + rules-fired with citations) → **sign off + produce the claim package** in Filing.

**The offer (de-risk the design partner):** a **90-day white-glove pilot** — you do the onboarding, they
put in one real product line, they walk out with **one real defensible claim** their broker will sign.
Pilot at a nominal/discounted flat fee that converts to standard SaaS on success. **Never contingency.**

**Pricing shape (flat-fee, compliance-clean):** self-filing importer ~$500–1,000/mo; broker / multi-client
~$2,000–5,000/mo + per-seat; optional one-time onboarding. Anchor against the **$125K** they'd pay a
specialist, not against other software.

---

## 4. What M0–M5 must prove to close them

Point every milestone at a specific objection it kills. (Engine + real-format ingest + sign-off gate are
**already built** — the foundation of the demo exists today.)

| Milestone | Objection it kills | Proof point the prospect sees |
|---|---|---|
| **M0** scaffold | *(internal — no customer surface)* | — |
| **M1** persistence + **designation ledger** | "This is just a one-shot calculator." | "Run your **whole book over time** — the ledger makes double-claiming (1313(v)) structurally impossible across every claim." |
| **M2** auth / RBAC / tenant isolation | "I can't put confidential import data in a toy." | "Your data is **isolated, encrypted, multi-user** — preparer, reviewer, your licensed signer, client read-only." |
| **M3** portfolio cockpit + work-queue | "Nice number — but is this a *tool I'd use*?" | "Your **daily cockpit**: every client, claim, deadline, and dollar in one queue." This is the **habit/lock-in**. |
| **M4** OCR document-intake | "My data is trapped in PDFs and emails." (the #1 onboarding killer) | "Drop your 7501s / commercial invoices / proofs of export — OCR **proposes**, you **confirm**, nothing auto-files." |
| **M5** reconciliation workbench + per-type **checklist** + Gaps & Chase | "Great estimate — but can I actually *file* it?" | "It walks you to a **fileable, defensible claim package** — the per-type checklist is satisfied, gaps are chased, your broker signs." |

### Minimum Sellable Pilot (the close)
- **To earn the "wow" / a verbal design-partner yes:** engine + ingest *(done)* + **M1** + **M5** →
  *one real defensible claim on their data*.
- **To convert to paid & retained:** **M2** (trust their data to it) + **M3** (the daily cockpit that
  creates lock-in) + **M4** (onboarding that doesn't drown them in manual entry).

So the build order that closes a customer is **M1 → M5 → M3 → M2 → M4** in *value-to-the-sale* terms, even
if engineering sequences them M0→M5. The thing that turns interest into a check is **M5** (a fileable
deliverable); the thing that makes the check *recur* is **M3 + the data lock-in from M1/M4**.

---

## 5. The sequence (run sales and build in parallel)

1. **Now, while M0–M2 build (not yet demoable on customer data):** do **customer discovery**. Build the
   50–100-name ICP list. Interview 10–20 — validate the pain, the contingency they pay, the data they have.
   Secure **1–2 verbal design partners** and (ideally) one **broker channel** ally. Cost: time only.
2. **When M1 + M5 land:** onboard the design partner on **one real product line**. Produce the claim.
   Get their broker to sign it **without rework** — that's the proof.
3. **When M2 + M3 land:** turn the pilot into a retained, paid, daily-use account. Ask for the logo + a
   reference + an intro to the next two.
4. **When M4 lands:** onboarding stops being white-glove and starts being repeatable → second and third
   customers without you hand-holding the data.

---

## 6. What "closed" looks like (pilot success metrics)
- **Recovered $X** in defensible drawback on the partner's *real* data.
- Estimate **matched their specialist's number within ~Y%** (or surfaced money they weren't claiming).
- Produced a claim package their **broker signed without material rework**.
- Partner **converts to a paid flat-fee subscription** and gives a **reference + one warm intro**.

Hit those four and you have a repeatable, un-copyable wedge — and the asset is now worth a profit multiple,
not "the cost of the code."

---

## 7. Guardrails on the whole motion (non-negotiable)
- **Flat fee, never contingency** (19 CFR 111.36(b); unlicensed-vendor trap).
- **A licensed party always signs & transmits** — the tool prepares; the sign-off gate enforces it.
- **You stay a software vendor**, never the operator/filer of record (CBP HQ H350722).
- **OCR proposes → human confirms → licensed signer certifies — nothing auto-files.**
- All pilot framing is **"preparation & decision-support,"** estimate-not-promise. (`docs/COMPLIANCE.md`)
