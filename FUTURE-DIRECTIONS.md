# FUTURE-DIRECTIONS

An honest record of where this could go — written at the point of publishing the repo as a
source-available portfolio piece (2026-06). For future-me, a collaborator, or a buyer. None of it is a
commitment; it's the distilled result of *building* the thing and then *validating the market*.

## Why it's a portfolio piece, not a company

The engine is complete and correct; the **market** is the problem. U.S. duty drawback is **saturated** for
a solo, sales-averse, $0-budget, unlicensed founder:

- The capability is already embedded in nearly every customs/trade platform — Descartes, WiseTech/CargoWise,
  SAP GTS, Oracle GTM, Thomson Reuters ONESOURCE, e2open, Flexport, C.H. Robinson — plus specialist shops
  (Charter, J.M. Rodgers, Comstock & Holt) and funded AI startups (Pax, Zollback, Forge).
- A no-revenue niche compliance asset realistically sells for ~$1–5K (often $0); the plausible acquirers
  already have drawback, so they'd build, not buy.
- Compliance forces a **sell/license-only** posture for an unlicensed vendor (CBP HQ H350722) — you cannot
  lawfully *operate* it. See [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md), [`docs/MONETIZATION.md`](docs/MONETIZATION.md).

So it's published for credibility and as a back-pocket option, not commercialized. Deciding *not* to pour
months more into a saturated market — after validating it — was the right call.

## The genuinely reusable asset

The portable core is **`engine/drawback/matching/mcmf.py`** — a domain-agnostic **exact min-cost-max-flow**
primitive — plus the **glass-box trace** and the **conservative rules-engine** pattern (`rules/`, `data/`).
The customs specificity is isolated, so the engine could be repointed at other "you're-owed-money /
eligibility / optimal-assignment" problems that need explainability.

## Adjacent domains explored — and the verdict

- **Section 301 / tariff refunds (the strongest candidate, mid-2026): DON'T — closing gold rush.** SCOTUS
  struck the IEEPA tariffs (Feb 20 2026); ~$166B refund pool; CBP's CAPE portal is already disbursing. It is
  *inbound-friendly* (importers actively search — the opposite of drawback) and importers **self-file** PSCs
  (so one could *operate* it, not just sell — the constraint drawback could never escape). **But** it's a
  time-boxed window closing entry-by-entry (180-day deadlines), already crowded (funded Gaia Dynamics / AI
  Fund; InteliGems already claims "glass-box"; every trade law firm), the lead-gen model is already live
  (TariffsTool, ConsumerShield), and CBP's *free* portal caps pricing. The old In re §301 (HMTX) refund hope
  is dead (SCOTUS denied cert Jun 15 2026).
- **The pattern worth hunting next:** high public awareness **+** low competition **+** a *durable* (not
  transient) opportunity where you can be **early**. Tariff refunds were 2 of 3 — missing "early."

## Monetization models that fit a sales-averse solo (validated — for the next idea)

- **Lead-gen / referral.** A free tool qualifies "you're owed $X"; sell the leads/referrals to the few
  providers who file (≈10–20% of their fee, or flat per-lead). You sign 2–3 buyers instead of selling to
  hundreds of end customers — fits "I hate sales." Catch: it needs **traffic**, so it only works in a
  high-awareness market (drawback has none; tariff refunds do).
- **Open-core.** Open-source the engine as the credibility magnet; sell a self-serve, flat-fee "Pro" tier
  (the Sidekiq model). The repo is the funnel; no demos, no calls. Best no-sales OSS money model — but yield
  scales with adoption, which a tiny niche caps.

## If someone wants to take this further

Start at [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) (the broker-OS roadmap; M0–M3 built, M4–M7 unbuilt),
[`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) (the legal posture), and [`docs/MONETIZATION.md`](docs/MONETIZATION.md).
The engine + its 158 tests are the asset; the market is the risk.
