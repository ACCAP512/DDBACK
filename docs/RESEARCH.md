# RESEARCH.md — Phase 0 Primary-Source Research

**As-of date for every finding: 2026-06-19.** This document is the research gate (PRD §3.5).
No engine business logic may encode a rule that is not traceable to a citation here.

**Sourcing method.** Findings were rebuilt from primary law — 19 U.S.C. § 1313 (Cornell LII
mirror of the U.S. Code; cross-checked against uscode.house.gov / OLRC and GovInfo), 19 CFR
Part 190 (Cornell LII eCFR mirror + GovInfo CFR XML), controlling Federal Circuit / CIT / SCOTUS
case law, CBP Form 7501 and the ACE ABI CATAIR Drawback (TFTEA) chapter, and 15 CFR 30.6. Vendor
and law-firm pages were used only as leads, never as the cited authority. Two access limitations
recurred and are flagged where they matter: **ecfr.gov and cbp.gov repeatedly hard-blocked
automated retrieval (HTTP 403)**, so CFR text here is from the Cornell LII / GovInfo primary
mirrors and CBP operational positions are corroborated through CSMS message numbers, the CATAIR
PDF, and the statute/regs rather than quoted from cbp.gov HTML. A human spot-check against the
live eCFR and current CSMS is advised before any number drives a real CBP filing.

> **⚠️ Litigation recency.** Tariff eligibility (§5/§18) is fast-moving and litigated. Everything
> in those sections is current to early-to-mid June 2026; re-verify CSMS and the CIT/Fed. Cir.
> dockets before shipping. This is why all time-sensitive eligibility lives in one dated config
> module (`engine/drawback/config/tariff_eligibility.py`).

---

## Headline corrections to the PRD's priors (the research wins — PRD §0 rule 1)

| # | PRD hypothesis | Finding | Effect on engine |
|---|---|---|---|
| C1 | "190.22 = unused calc; 190.32 = manufacturing calc" | **REVERSED.** §190.22 (Subpart B) = **manufacturing** substitution / §1313(b). §190.32 (Subpart C) = **unused** substitution / §1313(j)(2). | Map provisions to the correct comparator or every number is wrong. |
| C2 | "8-digit HTS substitution" | **Confirmed**, plus the **"other" basket exception**: if the designated 8-digit subheading's article description begins with "other," substitution drops to a **10-digit** match (and that 10-digit must not also begin with "other"). §1313(j)(5); 19 CFR 190.2. | HTS match logic must implement the "other"→10-digit fallback. |
| C3 | "Refunds up to 99% of eligible duties" | Magnitude right, phrasing wrong: 99% of duties **+ taxes + fees**, applied **per charge**, and for **substitution** capped at the **lesser of** import-side vs. comparator-side. A flat `0.99 × total_duty` over-refunds substitution. | Lesser-of must be per-line, per-charge. |
| C4 | "Substituted value cannot be less than designated" | **No such standalone eligibility rule exists** under TFTEA. Value enters **only** through per-unit averaging inside the lesser-of cap. | Do not gate eligibility on value; apply value only in the cap. |
| C5 | "MPF and HMF refundable" | True **today**, but HMF only since the **2004 amendment** (Pub. L. 108-429 §1557; *Texport*, Fed. Cir. 1999 had held HMF **not** refundable). | Current entries: both eligible. Config notes the pre-2004 seam. |
| C6 | "Excise substitution capped at substituted-merchandise tax" (19 CFR 190.22(a)(1)(ii)(C), 190.32(b)(3)) | **Judicially invalidated** — *NAM v. Treasury*, Fed. Cir. 2021. Text still printed in eCFR but unenforceable; applying it **under-refunds** excise drawback. | Engine does not apply the excise double-drawback cap (flagged in trace). |
| C7 | "IEEPA refunded via a separate CAPE mechanism" | **Confirmed and sharpened.** IEEPA tariffs **struck down by SCOTUS 2026-02-20**; refunds run through **CAPE** ("Consolidated Administration and Processing of Entries") in ACE — **not** drawback. IEEPA contributes **$0** to the drawback pool. | IEEPA excluded from drawback; surfaced as a separate CAPE track, labeled. |
| C8 | "Filing requires a licensed broker; software can't file" | **Partially corrected.** An importer may **self-file on its own account with NO broker** (19 CFR 111.2(a)). Filing does require an **ABI filer code** + certified software (the channel). Software may **prepare/compute/format/transmit** but may **not be the certifier/signer of record** (19 CFR 190.6). | Layer-3 posture: prepare + format; human/broker certifies. |
| C9 | "3 years from payment of claim" retention | **Outdated.** Post-TFTEA it is **3 years from LIQUIDATION** (19 U.S.C. 1508(c); 19 CFR 190.15). AP pays *before* liquidation, so the dates differ. | Lifecycle/retention clock keys off liquidation. |
| C10 | "$15B/yr unclaimed; 80% never file; Charter = 1/3" | **Unsourced vendor marketing (LOW confidence).** The well-sourced number is drawback **paid** ≈ **$1B (2019, GAO-20-182)** → **~$3.9B (2023)**, growing ~26%/yr. | Honest market framing in docs; no inflated TAM in UI. |

---

# Eligibility & computation

## Q1 — Drawback types (19 U.S.C. § 1313)

Source: 19 U.S.C. § 1313 — https://www.law.cornell.edu/uscode/text/19/1313 ; official text
https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title19-section1313 (verified verbatim).

| Subsection | Name | Distinguishing requirement |
|---|---|---|
| **§ 1313(a)** | Manufacturing — direct identification | The **actual imported** duty-paid merchandise is traced into the exported/destroyed article. |
| **§ 1313(b)** | Manufacturing — substitution | "Imported duty-paid merchandise **or merchandise classifiable under the same 8-digit HTS subheading number**" used in manufacture within 5 years; "notwithstanding the fact that none of the imported merchandise may actually have been used." |
| **§ 1313(c)** | Rejected merchandise | Imported goods nonconforming to sample/spec, shipped without consent, or defective, returned/exported/destroyed. |
| **§ 1313(j)(1)** | Unused — direct identification | The **same imported** merchandise exported/destroyed **without use** in the U.S. |
| **§ 1313(j)(2)** | Unused — substitution | "Any other merchandise (whether imported or domestic)" of the **same 8-digit HTSUS** subheading, exported/destroyed unused, in lieu of the import; possession/operational-control requirement. |
| **§ 1313(p)** | Petroleum derivatives | Special substitution regime for enumerated petroleum "qualified articles"; **own matching rules** — do not reuse (j)(2) logic. |

Other subsections noted: (b)(4) sought-chemical-elements special rule; (d) flavoring/medicinal with
domestic tax-paid alcohol; (g) vessels/aircraft for foreign account; **(l)** the regulatory hook for the
refund-calculation methodology (the 99%/lesser-of math lives in Part 190 by authority of (l)); **(r)**
filing time limits; (v) multiple-claim prohibition; (x) packaging material.

**MVP scope decision (see DECISIONS.md D-007):** fully build **§1313(j)(1)** and **§1313(j)(2)**
(unused merchandise — the primary persona's re-export case and the cleanest linkage problem). Encode
manufacturing **(a)/(b)** rules and the distinct manufacturing lesser-of comparator, and represent the
provision codes, but treat full BOM-based manufacturing matching as designed/partial. (c) rejected is
represented in types but not matched in MVP.

## Q2 — Substitution standard (8-digit, and the "other" exception)

**8-digit HTSUS standard — CONFIRMED** for both (b) and (j)(2). Verified verbatim:
- §1313(j)(2): other merchandise "classifiable under the **same 8-digit HTS subheading number** as such imported merchandise."
- §1313(b)(1): "imported duty-paid merchandise **or merchandise classifiable under the same 8-digit HTS subheading number**…is used in the manufacture."
- 19 CFR 190.2 defines **"Substituted merchandise or articles"**: "must be classifiable under the **same 8-digit HTSUS subheading number** as the designated imported merchandise." https://www.law.cornell.edu/cfr/text/19/190.2

**The "other" basket exception — § 1313(j)(5), verbatim:**
- (j)(5)(A): merchandise may **not** be substituted on the 8-digit basis "if the article description for the 8-digit HTS subheading number under which the imported merchandise is classified **begins with the term 'other'.**"
- (j)(5)(B): in that case substitution is allowed only if (i) both are classifiable under the **same 10-digit HTS statistical reporting number** and (ii) that 10-digit description **does not begin with "other".**

Mechanics the engine encodes (`rules/hts.py`):
1. Take the **8-digit** subheading of the **designated import**.
2. If its article description begins with "other" → 8-digit substitution disqualified.
3. Then allow substitution only if designated and substituted share the **same 10-digit** number **and** that 10-digit description does not begin with "other"; otherwise no substitution.

**Scope of the "other" rule.** The statute phrases (j)(5) "For purposes of paragraph (2)" (i.e., (j)(2)).
The **regulation applies the same rule to (b) via the single shared 19 CFR 190.2 definition**, which governs
both Subpart B (190.22) and Subpart C (190.32). **For correctness the engine applies the "other"→10-digit
logic to both (b) and (j)(2)** (the conservative, CBP-operational reading). Recorded as ASSUMPTION A-04.

**Schedule B convenience — § 1313(j)(6):** a claimant may test 8-digit sameness using the first 8 digits
of the 10-digit Schedule B number. A matching convenience, not a separate standard.

**No value-floor eligibility rule (corrects C4).** Verified absent from §1313(j)(2), (b)(1), (j)(5), and
19 CFR 190.11/190.22/190.32. Value enters only via **per-unit averaging** (19 CFR 190.2; 190.11(a)(2)).

## Q3 — The "lesser of" rule (exact computation)

> The single most important computation in the engine — and the two substitution types use **different
> comparators**, so they must not share a code path.

**§1313(j)(2) unused substitution — 19 CFR 190.32(b)(1)** (https://www.law.cornell.edu/cfr/text/19/190.32):
refund ≤ **99% of the lesser of**
- (i) duties/taxes/fees **paid on the imported (designated)** merchandise (on the **per-unit average value**
  of the designated entry-summary line, 19 CFR 190.11(a)(2)); **vs.**
- (ii) duties/taxes/fees that **would apply to the EXPORTED article if it were imported.**

190.32(b)(2) destruction: same, **reduced by the value of recovered/valuable materials**.
190.32(b)(3) excise: a substituted-tax limitation — **invalidated, see C6/Q6, not applied.**

**§1313(b) manufacturing substitution — 19 CFR 190.22(a)(1)(ii)** (https://www.law.cornell.edu/cfr/text/19/190.22):
refund ≤ **99% of the lesser of**
- (1) duties/taxes/fees **paid on the imported** merchandise; **vs.**
- (2) duties/taxes/fees that would apply to the **SUBSTITUTED merchandise (the manufacturing input) if imported** —
  **not** the exported finished article. Manufacturing-input value = "cost of acquisition or production" (190.11(d)).

**Per-unit averaging — 19 CFR 190.2:** "the equal apportionment of the amount of duties, taxes, and fees
eligible for drawback for all units covered by a single line item on an entry summary to each unit."

**Direct identification (j)(1):** no substitution comparator; refund = **99% of the duties/taxes/fees paid
on the identified imported units** that are exported/destroyed (subject to the same 99% and per-unit basis).

## Q4 — Time limits

**5-year window: import → complete-claim filing — CONFIRMED.** Verified verbatim:
- §1313(r)(1): "A drawback entry shall be filed or applied for…**not later than 5 years after the date on
  which merchandise on which drawback is claimed was imported.** Claims not completed within the 5-year period
  shall be considered **abandoned.**" Extension only if CBP caused the untimely filing.
- 19 CFR 190.51(e)(1): timely if transmitted "**not later than 5 years after the date on which the merchandise
  designated as the basis for the drawback claim was imported**"; otherwise **abandoned**.
- A claim is "complete" only when transmitted with import entry data, applicable CBP Form 7553 notice(s), and
  **evidence of exportation/destruction** (19 CFR 190.51(a)(1)); filing date = receipt of the complete claim.

Interaction the engine encodes (`rules/time_windows.py`):
- **Clock start** = **import (entry/importation) date** of the **designated** line.
- **Clock end** = **claim filing date**.
- **Export/destruction date** must be **after import**, **before the claim is filed**, and **within 5 years of
  import** (§1313(j)(1)/(j)(2) require export/destruction "before the close of the 5-year period…and before the
  drawback claim is filed").
- For manufacturing (a)/(b), manufacture must occur within the same 5-year-from-import window.
- A narrow §1313(r) major-disaster extension (up to ~18 months) exists but is not verbatim-verified; the engine
  uses the **default** rule (abandon after 5 years) and flags the rare exception as out of scope (ASSUMPTION A-09).

## Q5 — Refund percentage and fee/charge treatment

**99% — confirmed**, applied **per charge** (19 CFR 190.51(b)); substitution further capped at the lesser-of
(Q3). The 1% is the un-refunded slice of otherwise-eligible duties/taxes/fees — **not** a separate fee and **not**
the MPF/HMF. (A few provisions allow 100%, e.g., 1313(d); MVP uses 99% for (a)/(b)/(c)/(j).)

Charge eligibility — **19 CFR 190.3** (https://www.law.cornell.edu/cfr/text/19/190.3):

| Charge | Eligible? | Authority |
|---|---|---|
| Ordinary customs duties (incl. the Ch. 1–97 base rate) | **Yes** | 19 CFR 190.3(a) |
| **Section 301** (China, USTR) | **Yes** | Not excluded by 190.3(b); CBP CSMS #18-000419. Report Ch.99 subheading + underlying line. |
| **Section 232** (steel/aluminum/copper) | **No** | Presidential Proclamations "no drawback shall be available"; CSMS #18-000317; reaffirmed Apr 2026 (Fed. Reg. 2026-06960). Narrow derivative-manufacturing carve-out exists → exclude by default. |
| **IEEPA** (2025 reciprocal/fentanyl) | **N/A** | Struck down SCOTUS 2026-02-20; refunded via **CAPE**, not drawback. $0 to pool. |
| **Section 122** (balance-of-payments surcharge) | **Uncertain → exclude** | CIT Slip Op. 26-47 struck it (2026-05-07), on appeal; ≤150-day statutory life; no drawback guidance. |
| **MPF** (Merchandise Processing Fee, acct code 499) | **Yes** | 190.3(a); *Texport* (Fed. Cir. 1999). |
| **HMF** (Harbor Maintenance Fee, acct code 501) | **Yes (post-2004)** | 190.3(a); Pub. L. 108-429 §1557 reversed *Texport*'s HMF holding. |
| **AD / CVD** | **No** | 19 U.S.C. 1677h ("shall not be treated as…regular customs duties"); 190.3(b). |
| Federal excise taxes attaching on importation | **Yes** (99%) | 190.3(a); see Q6 re invalidated substitution cap. |

## Q6 — Double drawback / anti-double-counting

- **One export = one claim — § 1313(v):** "Merchandise that is exported or destroyed to satisfy any claim for
  drawback shall not be the basis of any other claim," except component credit/deduction. → each exported/destroyed
  unit anchors **exactly one** claim. Import side: per-unit averaging governs so the same duty dollars aren't
  designated twice. **This is the conservation constraint in the matcher.**
- **Excise "double drawback" cap (190.22(a)(1)(ii)(C), 190.32(b)(3)) — INVALID** per *NAM v. Treasury* (Fed. Cir.
  2021, aff'g CIT Slip Op. 20-9): contradicts §1313's "any" tax "notwithstanding any other provision of law." Text
  still in eCFR but unenforceable. **Engine does not apply it** (flagged in trace). (ASSUMPTION A-07.)
- **Liability / multiple claimants — §1313(k), (s), (v); 19 CFR 190.63:** claimant liable for the full amount;
  importer derivatively (joint and several). Designation by successor (§1313(s)) keeps a single designation chain.

## Q7 — Inventory / identification conventions

**19 CFR 190.14** "Identification of merchandise…by accounting method" (https://www.law.cornell.edu/cfr/text/19/190.14)
permits, for fungible non-serialized units: **FIFO** (190.14(c)(1)), **LIFO** (c)(2), **low-to-high** (c)(3, three
variants — the claimant-favorable convention: consume lowest-drawback units first, preserving higher-drawback units
to claim), **average** (c)(4). One method must be used consistently for all of a claimant's fungible inventory of a type.

> **Critical scope (ASSUMPTION A-08):** 190.14(a) states the accounting methods **do not apply where the law
> authorizes substitution.** Substitution eligibility is by **same-8-digit-HTS + per-unit averaging**, not FIFO
> tracing. So the engine uses 190.14 conventions only for **direct-identification (j)(1)** claims (which import lot
> supplies an exported unit); **substitution (j)(2)** matching is governed by the HTS + lesser-of + conservation rules,
> not by FIFO/low-to-high. The optimizer's freedom to assign within a bucket is the substitution analogue.

## Q8 — Proof requirements

- **(a) Duty-paid import:** import entry data in the claim — entry number, 10-digit HTSUS, **Import Tracing ID (ITIN)**
  (19 CFR 190.51(a)(1)-(2)); duties must be on an entry whose **liquidation became final** (190.3(a)); 7501 + proof of
  payment substantiate amounts.
- **(b) Export:** 19 CFR 190.72 "Establishment of exportation" — date + fact of export + exporter identity; acceptable
  evidence includes **bill of lading, air waybill, freight/cargo manifest**, records from CBP-approved electronic export
  systems, the **AES ITN**, postal records. **Destruction:** 19 CFR 190.71 — file **CBP Form 7553 ≥7 working days**
  before destruction; if CBP doesn't witness, a **disinterested third party** (e.g., landfill operator) attests; deduct
  **recovered-materials** value. Rejected-merchandise: 190.42 (Form 7553 ≥5 working days prior).
- **(c) Link:** carried by the claim's **ITINs/MTINs** and certifications (19 CFR 190.51(a)(2)); direct-ID uses the
  190.14 accounting method, substitution uses the 8-digit match + per-unit averaging.

(Note: in modern Part 190, destruction evidence is §190.71/§190.42; the legacy "§191.175" cite is old Part 191.)

---

# Filing & operating model

## Q9 — Who may file

Three severable acts (19 CFR 190.6; Part 111; CBP "Drawback in ACE"):
- **Prepare/compute/format:** software/claimant/service-provider may do this. "Mere electronic transmission of data"
  and "corporate compliance activity" are carved out of "customs business" (19 CFR 111.1).
- **Transmit to ACE via ABI:** requires a CBP **entry filer code** + certified ABI software (self-filer, broker, or
  service-bureau filer).
- **Sign / certify / be filer of record:** must be a natural person — claimant's authorized officer/employee/owner with
  POA, an individual on own behalf, **or a licensed customs broker/attorney with POA** (19 CFR 190.6). **Software cannot
  be the certifier.**
- **Self-file without a broker is permitted** for an importer "transacting customs business solely on his own account"
  (19 CFR 111.2(a)). Three CBP paths: self-file (own filer code), licensed broker, or service provider transmitting a
  **claimant-constructed** claim.

**Product posture:** Drawback Engine is **preparation/decision-support** — it computes, formats, and can produce the
ACE/ABI transmission, but the **claimant or its licensed broker/attorney certifies and files**. (Guardrail in UI + README.)

## Q10 — Privileges (timing levers)

- **Accelerated Payment (AP) — 19 CFR 190.92:** payment of estimated drawback **before liquidation**; needs a written
  application and a sufficient **1A bond**; CBP decides within **90 days**; once accepted, payment **usually ~3 weeks**.
  Turns a 1–3 year wait into weeks.
- **Waiver of Prior Notice (WPN) — 19 CFR 190.91:** waives prior notice of intent to export/destroy for (j) and (c)
  claims; 90-day decision. Removes the pre-export bottleneck.

## Q11 — Recordkeeping & audit

Retention = **3 years from LIQUIDATION** of the claim (19 U.S.C. 1508(c)(2); 19 CFR 190.15; corrects C9). Records must
independently establish each element (import, qualification, export/destruction). Verification framework: 19 CFR Part 190
Subpart F.

## Q12 — Liability (sets the conservatism bar)

**19 U.S.C. 1593a:** false/excessive drawback by **fraud** → penalty up to **3× revenue loss**; **negligence** → up to
**20%** (first), **50%** (repetitive), **100%** (subsequent); **"electronically transmitted data" is in scope.** §1593a(d):
deprived duties **restored whether or not** a penalty is assessed (clawback + interest). 19 CFR 190.63: claimant liable
full amount; importer joint and several. Criminal exposure under 18 U.S.C. 542/550/1001 for knowing falsity. → **the engine
must never fabricate a value, must flag missing proof rather than auto-fill, and must keep the human-certification gate.**

## Q13 — Claim lifecycle states

`TRANSMITTED → ACCEPTED (ACE, immediate accept/reject) → COMPLETE (DIS docs ≤24h)` then either the **AP branch**
(AP privilege + valid 1A bond → estimated payment ~3 weeks) or straight to **UNDER REVIEW / (SUSPENSION possible)** →
**LIQUIDATED** (ACE liquidates weekly, Fridays; liquidation fixes the final amount and starts the 3-year clock) →
**PAID** (no-AP refund ~3 weeks after decision) / **AP TRUE-UP** (repay any AP excess) → optional **PROTEST** (≤180 days,
19 U.S.C. 1514). AP is provisional cash; claim stays open until liquidation.

---

# Data

## Q14 — Entry summary / CBP Form 7501 fields (drawback-relevant)

Source: CBP Form 7501 + block-by-block instructions (rev. 02/26). Header blocks 1–30; line items cols 31–38; totals
39–44. Drawback-relevant fields the parser maps:

- **Entry header:** Filer Code/Entry Number (blk 1, `XXX-NNNNNNN-N` — join key to a claim), Entry Type (2), **Entry
  Date** (7) and **Import Date** (11, the two dates that start the 5-year clock), Country of Origin (10), **Importer of
  Record Number** (27, IRS/EIN — claimant key), MID (13).
- **Line items (one per commodity/country):** Line No. (31), Description (32), **HTSUS 10-digit** (33A, e.g.
  `8501.31.4000`), per-line fee tags incl. **MPF/HMF** (33D), Net Quantity in HTSUS units (35), **Entered Value** (36A,
  basis for the 99% calc), HTSUS Rate (37A), I.R.C. excise rate (37C), **Duty and I.R. Tax** (38).
- **Totals / Other Fee Summary:** each fee carries a 3-digit accounting code — **MPF = 499, HMF = 501**, AD = 012, CVD =
  013. Parser must read fee amounts **by code**, not just the block-44 total.

## Q15 — Export proof data (EEI / AES — 15 CFR 30.6)

Mandatory EEI elements (filed in AES; returns an **ITN** as proof): USPPI name/address/ID (EIN), **date of export**,
ultimate consignee, U.S. state of origin, **country of ultimate destination** (ISO), mode of transport, carrier + **SCAC/
IATA**, **port of export** (Schedule D), related-party indicator, domestic/foreign indicator, **commodity classification
(10-digit Schedule B or HTSUS)**, description, **unit of measure + quantity**, shipping weight, **value at port of export**.
Conditional: intermediate consignee, FTZ id, ECCN/license, **in-bond code + import entry number**, original ITN. A **bill
of lading / air waybill** is the classic documentary export proof: shipper, consignee, carrier+SCAC, vessel/voyage, ports,
**on-board/departure date** (= export date), description, weight, B/L number. The CATAIR export record carries a **BOL
Indicator + BOL Carrier Code (SCAC)**, confirming CBP accepts a B/L reference as the export-proof element.

## Q16 — HTSUS structure

10-digit hierarchy. First **6 digits** = international HS (WCO). Digits **7–8** = U.S. legal **tariff-rate line** (carries
the duty rate; **legal text of the HTS ends at 8 digits**). Digits **9–10** = U.S. statistical suffix (no duty effect).
Example `8501.31.20.00`: `85` chapter (electrical machinery) → `8501` heading (motors/generators) → `8501.31` HS subheading
(DC motors ≤750W) → `8501.31.20` 8-digit rate line → `.00` statistical. **Substitution keys on the 8-digit prefix.**

## Q17 — CATAIR drawback chapter (claim transmission layout)

Source: ACE ABI CATAIR Drawback (TFTEA) v26 (read in full). Fixed **80-char** records; input filing app id **`DE`**.
Record skeleton: **10** Entry Summary Header → **40** Imports detail (filer code+entry number+**CBP ES line#** point at the
exact 7501 line; carries **ITIN** + **Drawback Accounting Method Code**) → **41** Import classification (10-digit HTS +
description) → **42** Import quantity/UOM + **Entered value per unit** + **Substituted value per unit** (drive the lesser-of)
→ **43** Import revenue claimed (Accounting Class Codes **364 Drawback Duty, 365 Tax, 398 HMF, 399 MPF**; "99% of the duties,
taxes, and fees") → (**50–53** manufactured articles + links, for (a)/(b)) → **70/71** TFTEA export/destroy articles + desc
(date, qty, UOM, country, **BOL indicator + SCAC**) → **72** links export→import ITINs → **89/90** revenue totals.
**Appendix A provision codes:** 08/58 = §1313(j)(1); **09/59 = §1313(j)(2)**; 01/51 = §1313(a); 02/52 = §1313(b);
03–06/53–56 = (c). The four common mid-market types are 08/58, 09/59, 01/51, 02/52.

## Q18 — Realistic formats, sizing, and the eligible-pool reality

**Formats / ingestion surface:** cleanest is an **ACE Reports / ITRAC CSV/Excel** entry-summary line export (row per line,
with entry number, 10-digit HTS, entered value, duty/MPF/HMF, import & entry dates) — build the primary parser to this.
Also: **PDF 7501s** (OCR), **broker CSVs** (idiosyncratic headers → per-broker mapping), **ERP exports** (export/sales side
+ BOMs), and reconstructed export proof (invoice + B/L + AES ITN). The CATAIR `DE` fixed-width file is the **output** target.
**Sizing (5-year window):** mid-market importer ≈ hundreds–few thousand entries/yr × handful–dozens of lines ≈ **10⁵–10⁷
entry-summary lines**; export/sales side often 2–10× larger. Matching join is keyed on **8-digit HTS + dates within window**
— the heaviest op; decompose per HTS bucket. (Row-count ranges are engineering estimates, not a CBP statistic.)

**Market reality (Q16/Q17 of the market brief):** "$15B unclaimed / 80% never file / Charter = 1/3" are **LOW-confidence
vendor/SEO marketing**, mathematically strained against the sourced figures. **Drawback actually paid ≈ $1.0B (FY2019, GAO-
20-182, to Congress, HIGH confidence) → ~$3.9B (FY2023, brokers citing CBP, MED), ~26%/yr post-TFTEA growth.** The closest
real participation stat: J.M. Rodgers' "~12–15% of eligible SMBs file." **The reliably drawback-eligible special-tariff pool
is Section 301 + MPF + HMF + ordinary customs duties** — IEEPA and 232 (the largest 2025 headline layers) are **out**, so an
honest estimate is a fraction of headline "tariff exposure." Competitive white space that survives scrutiny: **instant,
self-serve eligibility + a glass-box (fully explainable) number with no human gate** — incumbents (Charter, J.M. Rodgers) and
even the 2026 "AI" entrants (Zollback, Tariff Refund HQ) are all **managed services** gated behind a sales call. "AI/fast/
contingency" is saturated; **self-serve + glass-box is the genuine wedge.**

---

## Source index (primary)

**Statute (19 U.S.C., via law.cornell.edu/uscode/text/19/…):** §1313 (types, substitution, (j)(5) "other", (l) calc, (r)
time limit, (v) one-claim, (k)/(s) liability); §1508 (recordkeeping, 3-yr-from-liquidation); §1593a (penalties); §1677h
(AD/CVD not regular duties); §1514 (protest).
**Regulations (19 CFR, via law.cornell.edu/cfr/text/19/…):** Part 190 — §190.2 (defs incl. substituted merchandise,
per-unit averaging), §190.3 (eligible charges; AD/CVD exclusion), §190.6 (who may sign), §190.11 (valuation), §190.14
(accounting methods), §190.15 (retention), §190.22 (manufacturing substitution lesser-of), §190.32 (unused substitution
lesser-of), §190.42/.71/.72 (proof of export/destruction), §190.51 (completion/timeliness), §190.62/.63 (penalties/liability),
§190.91 (WPN), §190.92 (AP), Subpart F (verification); Part 111 §§111.1–111.2 (broker licensing/self-file).
**Case law:** *Texport Oil v. United States*, 185 F.3d 1291 (Fed. Cir. 1999) (MPF yes / HMF no, pre-2004); *NAM v. Treasury*
(Fed. Cir. 2021) (excise double-drawback cap invalid); *Trump v. V.O.S. Selections* / *Learning Resources v. Trump*, 605 U.S.
___ (2026-02-20) (IEEPA tariffs struck). Statutory fix: Pub. L. 108-429 §1557 (2004, HMF).
**CBP / technical:** Form 7501 (rev. 02/26) + instructions; ACE ABI CATAIR Drawback (TFTEA) v26; CSMS #18-000419 (301 yes),
#18-000317 (232 no); CAPE (IEEPA refunds, launched 2026-04-20); 15 CFR 30.6 (EEI); USITC HTS structure.
**Market:** GAO-20-182 (Dec 2019, ~$1B/yr paid); CBP FY2023 Trade Fact Sheet; J.M. Rodgers / C.H. Robinson (CBP-cited
~$3.9B FY2023). Tariff-litigation: CIT Slip Op. 26-47 (§122); Fed. Reg. 2026-06960 (§232 Apr 2026).

> Access caveats restated: ecfr.gov and cbp.gov blocked automated fetch — CFR text from Cornell LII / GovInfo mirrors,
> CBP positions corroborated via CSMS numbers + CATAIR + statute/regs. §190.22(a) body sourced from LII (eCFR mirror), not
> re-confirmed byte-for-byte on GovInfo. Tariff/litigation items current to ~early-June 2026. Re-verify before live filing.
