# COMPLIANCE.md — legal posture & readiness plan

**Date:** 2026-06-19 · Synthesizes three primary-source legal-research streams (customs-business &
UPL; data confidentiality & privacy; IP cleanliness & assignability) plus a dependency-license audit.
**This is compliance research, not legal advice — a customs attorney and a privacy/IP attorney must
review the specific structure, contracts, and EEI-handling model before any real client data or any
sale. "Have counsel confirm before go-live" applies to everything below.**

---

## 0. Verdict — are we compliant?

**The product can be fully compliant, and the planned business model (sell / flat-fee-license, not
operate) is precisely the clean legal path. But it is not "compliant as-is" — three things must change
before it touches a real user or real data, and one fact must be confirmed.**

- ✅ **The sell/license model is clean.** A January 2026 CBP ruling on almost this exact fact pattern
  (HQ H350722) holds that an unlicensed party *operating* such a tool to produce drawback figures/claims
  for importers is unlawful **customs business** (up to $10,000 *per transaction*) — **but selling or
  flat-fee-licensing the software to a licensed broker, or to an importer self-filing its own account,
  who operates it under their own judgment, makes you a software vendor, not a customs-business actor.**
  Your plan and the legal path are the same path.
- ✅ **The data architecture is already right.** EEI (export) data is *statutorily confidential*
  (15 CFR 30.60); the risk is disclosing it to a hosted third party. The product's **local, no-retention,
  "nothing is sent" design avoids that at the root** — preserve it as the default.
- ✅ **The IP is unusually clean and assignable.** The encoded law is public-domain (17 U.S.C. 105 +
  *Georgia v. Public.Resource.Org*); the dependency tree is permissive-only (no copyleft) with a
  stdlib core; AI-assisted code is ownable and assignable (the AI vendor's terms assign output to the
  developer; substantial human authorship is documented). The work before sale is **paperwork, not
  surgery.**
- ⚠️ **Three required changes** (detail in §4): reframe "you're owed $X" → a disclaimed **estimate**;
  add a **mandatory, logged licensed-filer sign-off** before any claim file is final; add **disclaimers
  + an EULA field-of-use restriction + a DPA + a privacy policy**, and keep pricing **flat-fee** (never
  a % of refunds — that re-triggers customs-business / fee-splitting under 19 CFR 111.36(b)).
- ✅ **Chain of title confirmed clean (2026-06-19):** built solo, **not employed** during development, no
  contractors/co-authors, no employer IP-assignment in play. The one title risk is cleared — IP is fully
  assignable.
- ❌ **The one thing not to do:** never *operate* the tool as a paid service that produces drawback
  determinations/claims for third-party importers. That is customs business requiring a license, and a
  disclaimer will not cure it.

### Who bears the compliance burden (this is the point of selling/licensing)
The product is like TurboTax/QuickBooks or a tariff calculator: **the operator carries the regulated
burden, the vendor carries only its own conduct.**
- **The OPERATOR (licensed broker, or importer self-filing its own account) bears:** the customs-business
  judgment, the filing, the claim's accuracy and any CBP penalty (they sign), EEI confidentiality (they
  hold the data), and recordkeeping. **This is most of the legal weight, and it is not yours.**
- **The VENDOR (you) bears only three things, regardless of who operates:** (1) **your own marketing
  claims** — you can't deceptively over-promise (FTC §5; the DoNotPay seller was the one punished); (2)
  **licensing it for lawful use** — the EULA field-of-use restriction is what *effects* the burden-shift
  and avoids aiding-unlicensed-use exposure; (3) at a sale, the **IP reps** (clean here).
- **Today, with no clients and only simulated data, there is essentially no live exposure at all** — no
  customs business is happening, no real EEI is processed. The trigger is the first public marketing claim
  or the first byte of real client data. The work is to put the thin vendor wrapper (1)-(3) in place
  *before* that moment.

---

## 1. Regime 1 — Customs business & unauthorized practice (the operate-vs-license line)

**Authority:** 19 U.S.C. 1641; 19 CFR 111.1 / 111.2 / 111.36(b); **CBP HQ H350722 (Jan 16, 2026)** and
the rulings it relies on (H290535, H272798, H326926, H068278, 114654); *Delgado v. United States* (CIT
2008). UPL: *UPLC v. Parsons Tech.* (5th Cir. 1999) + Tex. Gov't Code 81.101(b); *LegalZoom v. NC State
Bar* (2015) + N.C. Gen. Stat. 84-2.2; **FTC v. DoNotPay (2025)**.

**The line (verified):** "Customs business" *expressly includes* drawback and the *preparation* of
documents "intended to be filed with CBP… whether or not signed or filed by the preparer." So "we don't
transmit to CBP" is **necessary but not sufficient.** What's dispositive is **who exercises the judgment
and on whose behalf**:
- **Operate it yourself (unlicensed) for importers → prohibited customs business** (the engine *is* the
  "decision matrix"; HQ H290535 holds a disclaimer doesn't cure it; HQ H326926 holds after-the-fact
  broker review doesn't cure it).
- **License/sell to a licensed broker** → the broker is the licensed decision-maker; you're an ABI-style
  software vendor. Clean.
- **License/sell to an importer self-filing its own account** → exempt under 19 CFR 111.2(a)(2)(i); you
  sell a tool, you act for no one. Clean.

**UPL & FTC:** an automated tool that runs the *user's own data* through *transparent, citation-backed
logic*, conspicuously disclaimed as software (not a substitute for a licensed broker/attorney), sits on
the protected "self-help tool" side (Parsons; NC §84-2.2). The actively-enforced risk is **marketing**:
DoNotPay was punished under FTC §5 for unsubstantiated "AI replaces a professional" claims — so a
**reliance-inducing "you're owed $X" promise is the trap.** The glass-box, `[VERIFIED]/[INFERRED]/[GUESS]`,
conservative-range design is the *right* instinct — it substantiates and bounds the claim.

**Required mitigations (Regime 1):**
1. **Lock the sell/license model in the EULA** — lawful use only: operated by a licensed customs
   broker/attorney, or by an importer/exporter solely on its own account. **Do not operate a "we'll prep
   it for you" service.**
2. **Flat software fee only** — no % of recovery, no per-claim/per-entry fee (19 CFR 111.36(b)
   fee-splitting; HQ H276784/H290002).
3. **Mandatory, logged licensed-filer (or self-filer) sign-off** before any CATAIR file is final — the
   human decision (rule selections, matches, figures) must be *theirs*, recorded. HQ H350722: "the actual
   decision… must be made by a duly licensed customs broker," who "must have a role in specifying" what
   the tool generates.
4. **Reframe the headline as a disclaimed estimate** — "estimated potential recovery, subject to review
   and filing by a licensed customs broker," not "you're owed $X."
5. **Conspicuous, repeated disclaimer** (onboarding, every estimate, the claim export): "Decision-support
   software. Not a customs broker, law firm, or accountant, and not a substitute for a licensed filer.
   Does not transact customs business or file with CBP. A licensed filer must independently review and
   file." (Tracks Tex. §81.101(b) and NC §84-2.2(a)(3).)
6. **Have a licensed customs broker/attorney review the engine's drawback rule-logic + CATAIR template**
   (mirrors NC §84-2.2(a)(2)); keep the reviewer on record.
7. **Never market it as replacing a broker/attorney or as a guaranteed refund** (FTC §5); substantiate
   accuracy with the test suite.
8. **Open items for counsel:** an opinion on the specific EULA/structure citing HQ H350722, and consider
   a CBP ruling request (19 CFR Part 177) on this exact tool-vendor model for certainty (CBP has blessed
   decoupled, disclaimed tools — HQ H272798).

---

## 2. Regime 2 — Data confidentiality, privacy & security

**Authority:** 13 U.S.C. 301/305; **15 CFR 30.60 (EEI confidentiality)**, 30.1/30.3 (authorized agent),
30.10 (5-yr retention); 19 CFR Part 103 + 18 U.S.C. 1905 (trade-secret-grade entry data); 19 CFR 111.24
(broker confidentiality, flows down); CCPA/CPRA (B2B exemption expired 2023; service-provider terms,
Cal. Code Regs. 11 §7051); GDPR Art. 28.

**The keystone:** EEI is confidential and **may not be disclosed by the USPPI/agent for nonofficial
purposes** — and disclosure to a *third-party SaaS vendor* is exactly the enumerated risk. **It falls on
the customer, and it is avoided entirely by local/customer-controlled processing — which the product
already does.** This is the single most important data fact: keep EEI/entry processing local and
non-retained by default. If a hosted mode is ever built, only ingest EEI server-side as the customer's
written-authorized representative (15 CFR 30.3) under strict use-limitation terms.

**Required mitigations (Regime 2):**
1. **Local / customer-controlled processing as the default and marketed posture** (the keystone control).
2. **True non-retention** — compute ephemerally; delete inputs and the generated CATAIR/trace at session
   end; make the "not stored, not shared" claim factually true.
3. **A DPA / service-provider addendum** with every real-data engagement — one doc that satisfies CCPA
   service-provider terms (no retention/use/disclosure beyond the service; no sale/share/combine), GDPR
   Art. 28 if EU personal data appears, and confidentiality flow-down for brokers' 19 CFR 111.24 duty.
4. **A public privacy policy** (covers users' own account/contact data; no-sale stance); minimize
   personal contact fields collected.
5. **Encryption (TLS 1.2+ / AES-256) + access control + an access-audit log** for anything that persists
   (separate from the per-line correctness trace).
6. **Keep the "SIMULATED — NOT TRANSMITTED" gate** until a licensed filer reviews and transmits.
7. **Surface the dual retention clocks** in guidance (EEI 5 yr from export; drawback records 3 yr from
   liquidation) — and don't imply *you* retain them; the customer does.
8. **Sequence SOC 2:** security questionnaire + one-page control brief now → SOC 2 Type I when a customer
   first requires it → Type II at scale. **No SOC 2 needed for a controlled, local, no-retention pilot.**
9. **Scope to reality:** you're very likely below CCPA "business" thresholds (so you're a *service
   provider*, not a covered business); GDPR generally isn't triggered for a US-broker/US-transaction tool
   unless EU natural persons appear — don't over-build EU machinery.

---

## 3. Regime 3 — IP cleanliness & assignability (sale-readiness)

**Authority:** 17 U.S.C. 105; *Georgia v. Public.Resource.Org* (2020); *Banks v. Manchester*;
*Feist* (facts/systems uncopyrightable); U.S. Copyright Office *AI Copyrightability* report (Jan 2025);
*Thaler v. Perlmutter* (cert. denied 2026); AI-tool ToS (output assigned to user); 17 U.S.C. 204(a).

- **Encoded law = public domain.** 19 U.S.C. 1313, 19 CFR Part 190, case law, HTSUS/USITC, Schedule B,
  CATAIR — all U.S. Government works / government edicts. The engine encodes *logic and structure* (and a
  self-authored HTS fixture), copies no licensed dataset. **No third-party copyright encumbrance.** The
  `docs/RESEARCH.md` clean-room record is strong diligence evidence — preserve it.
- **Dependencies = permissive only.** MIT (React/Radix/TanStack/Recharts/Vite), Apache-2.0 (TypeScript,
  python-multipart), BSD (uvicorn/httpx); **stdlib-only engine core. No GPL/LGPL/AGPL/MPL.** Only duties:
  retain attribution/NOTICE texts (a `THIRD-PARTY-NOTICES` file).
- **AI-assisted code is ownable & assignable.** Human-authorship is required (*Thaler*), but AI-*assisted*
  work is copyrightable where there's substantial human selection/arrangement/modification (Copyright
  Office 2025) — which the PRD-directed, architecture-chosen, primary-source-verified, reviewed build
  demonstrably is. The AI vendor's commercial terms **assign output ownership to the developer**; no
  vendor chain-of-title break. Honest nuance to *disclose, not hide*: purely-machine-generated fragments
  may carry thin/no copyright, so part of the moat rests on trade-secret + the protectable
  compilation/arrangement + domain-correctness, not on locking every literal line.
- **Title = solo & clean.** Single git author, no contractors/co-authors, clean-room (no vendor content).
  **The one item to clear: the employment/moonlighting question.**

**Required IP paperwork (Regime 3):**
1. **Clear the employment question** — declaration that it was built on personal time/equipment outside
   any employer's scope; obtain a written employer IP-waiver if there's any overlap. *(Highest-priority
   title item.)*
2. **Add `LICENSE`** (the proprietary terms the asset is sold under — currently none at repo root),
   **`THIRD-PARTY-NOTICES`** (bundled MIT/BSD/Apache license texts), an **SBOM** (SPDX/CycloneDX from
   `package-lock.json` + `requirements.txt`, incl. transitive), and **`AI-DISCLOSURE.md`** (tool, tier,
   that output was assigned to the developer + terms complied with; retain the ToS version in force).
3. **Preserve the human-authorship & clean-room exhibits** (PRD, commit history, RESEARCH/ASSUMPTIONS/
   DECISIONS, the `[VERIFIED]/[INFERRED]/[GUESS]` tags) as the diligence pack.
4. **For the sale:** a §204(a) IP assignment (copyright + trade secrets + all IP, further-assurances +
   Copyright Office recordation) and the reps: ownership/title, non-infringement, no-employer-claim,
   OSS-disclosure schedule, **AI-tools-used disclosure**, public-domain-content rep, synthetic-data/no-PII
   rep. Consider an IP indemnity / R&W insurance for the AI/OSS reps.

---

## 4. Required in-product changes (the compliance-driven product work)

| # | Change | Regime | Effort |
|---|---|---|---|
| P1 | Reframe headline "you're owed $X" → "estimated potential recovery — subject to review & filing by a licensed customs broker"; tighten all claim copy to estimate-not-promise | 1 (FTC/UPL) | small |
| P2 | Conspicuous disclaimer at onboarding, on every estimate, and in the claim export (per §1.5 text) | 1 | small |
| P3 | **Mandatory, logged licensed-filer / self-filer sign-off** before a CATAIR file is "final"; the human affirmatively accepts rule selections, matches, and figures; recorded with name/role/timestamp | 1 (the dispositive one) | medium |
| P4 | EULA field-of-use gate enforced in-app (attest: licensed broker/attorney, or self-filing own account) + flat-fee posture | 1 | small |
| P5 | Make local/no-retention real and visible (no server-side EEI ingestion; ephemeral compute; "not stored" claim true); add a data-handling notice | 2 | small–med |
| P6 | A per-claim **defensibility report** (rules fired + tier + citation + the reconciliation check) so a licensed filer validates from the trace alone — strengthens the §1.3 "human decision is theirs" posture *and* the pilot success criteria | 1 + correctness | medium |

(P3 and P6 are the same backend hardening previously paused — now compliance-justified, not optional.)

---

## 5. The get-product-ready plan

Goal: get to **(a) demo-ready, (b) pilot-ready on real broker data, (c) sale/diligence-ready** — compliant
throughout. Phased by impact ÷ effort; marked **[build]** (I can do) vs **[you]** (owner/attorney).

> **STATUS (2026-06-19): the [build] items in Phases 1–3 are DONE and verified** — estimate-not-promise
> reframe leading with the defensible figure, conspicuous disclaimers + EULA field-of-use gate, the
> `defensibility.py` hardening + report view, the `filing/signoff.py` sign-off gate, real-format ingestion
> + `make demo`, the IP/diligence pack, and the `legal/` templates. **Remaining = [you] items:** confirm
> the title declaration (employment cleared), and engage counsel to finalize the EULA/DPA and (optionally)
> a CBP ruling request before real client data or a sale.

### Phase 0 — Confirm & engage (unblocks everything; start now)
- **[you]** Answer the **employment/moonlighting** question (Regime 3 #1). The one title risk.
- **[you]** Line up a **customs attorney** (EULA/structure opinion + optional CBP ruling request) and a
  **privacy/IP attorney** (DPA + IP assignment). Everything below is built to *their* review.

### Phase 1 — Compliance + IP paperwork (fast, mostly non-code; makes the asset shareable & clean)
- **[build]** In-product P1, P2, P4, P5 (reframe estimate, disclaimers, EULA gate + attestation,
  local/no-retention notice).
- **[build]** IP pack: `LICENSE`, `THIRD-PARTY-NOTICES`, SBOM, `AI-DISCLOSURE.md`; preserve provenance
  exhibits.
- **[build]** Draft **templates** (for attorney finalization, not legal advice): EULA + field-of-use,
  disclaimer copy, a DPA/service-provider addendum, a privacy policy, and the IP-assignment + reps
  schedule.

### Phase 2 — Pilot-readiness on real data (the code build)
- **[build]** **P3 — mandatory licensed-filer sign-off gate** + audit log (compliance-critical).
- **[build]** **P6 — correctness hardening + per-claim defensibility report** (the structurally-defensible
  VERIFIED-only headline, the reconciliation invariant that *raises* on violation, the report) — the
  glass-box artifact a broker validates from, and the pilot's success criterion.
- **[build]** **Real-format ingestion** (NetSuite commercial spine + CBP 7501/ACE entry-summary + AES/EEI
  export-proof → the engine's input contract), so a broker pilot runs *their* data — with local processing
  preserved (no server-side EEI).
- **[build]** A realistic demo dataset + `make demo` end-to-end (ingest → estimate → trace → claim).

### Phase 3 — Diligence pack + demo polish (sale-ready)
- **[build]** A **data-room outline** + the clean-room/IP exhibits + a one-page security/privacy brief.
- **[build]** Ungated, public demo carrying the new estimate framing + disclaimers (the $0 GTM hook from
  `docs/MONETIZATION.md`).

### Phase 4 — Counsel sign-off & go (owner/attorney)
- **[you]** Attorney finalizes EULA/DPA/privacy/IP-assignment; optional CBP ruling request; then the demo
  is public and the pilot/sale conversations (per `MONETIZATION.md`) begin.

---

## 6. Sources (load-bearing)
**Customs/UPL:** 19 U.S.C. 1641; 19 CFR 111.1/111.2/111.36 (law.cornell.edu); CBP HQ H350722, H290535,
H272798, H326926, H068278, 114654 (rulings.cbp.gov); *Delgado* (CIT 2008); *UPLC v. Parsons* 179 F.3d 956
(5th Cir. 1999); Tex. Gov't Code 81.101(b); *LegalZoom v. NC State Bar* 2015 NCBC 96 + N.C.G.S. 84-2.2;
FTC DoNotPay order (Feb 2025, ftc.gov). **Data:** 13 U.S.C. 301/305; 15 CFR 30.60/30.1/30.3/30.10 (ecfr/
census.gov); 19 CFR Part 103 + 18 U.S.C. 1905; 19 CFR 111.24; CCPA/CPRA (oag.ca.gov; Cal. Code Regs. 11
§7051); GDPR Art. 3/28. **IP:** 17 U.S.C. 105/103/204(a); *Georgia v. Public.Resource.Org* 590 U.S. 255
(2020); *Banks v. Manchester* 128 U.S. 244; *Feist* 499 U.S. 340; U.S. Copyright Office *AI
Copyrightability* report (Jan 29, 2025); *Thaler v. Perlmutter* (D.C. Cir. 2025, cert. denied 2026);
Anthropic Commercial Terms (output assignment); Apache-2.0 license. Full URLs in the research transcripts.

> Reiterated: compliance research, not legal advice. A customs attorney and a privacy/IP attorney must
> confirm the EULA/structure, the EEI-handling model, and the asset-sale documents before go-live.
