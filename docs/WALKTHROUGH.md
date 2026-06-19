# WALKTHROUGH.md — the demo, end to end

A reviewer's tour. Takes ~3 minutes. Everything runs locally on synthetic data; no CBP connection.

## 0. Run it

```bash
make setup     # venv + Python deps + build the SPA + generate samples
make run       # http://localhost:8000
```
Open **http://localhost:8000**.

(Or dev mode: `make dev` for the API, then `cd web && npm run dev` for the hot-reloading SPA on :5173.)

## 1. Layer 1 — the instant eligibility magnet

Click **"Load sample data."** In well under a second you get an on-screen estimate for the synthetic
persona — *Apex Electronics Importing LLC*, a mid-market importer of Section-301 Chinese components that
re-exports finished goods and unsold inventory.

What you see:
- **The hero number:** "You're owed approximately **$3.79M**," with the conservative **range** drawn as a
  bar from the **low end ($1.68M)** to the **point ($3.79M)**. One sentence explains it: the headline is the
  *defensible, proof-backed* recovery from 163 matched import↔export pairs; the low end excludes speculative
  Section 301 from the substitution comparator. A secondary pill shows **+$0.52M pending review**.
- **A dated banner:** "Tariff eligibility as of **2026-06-19**," with chips for what's **eligible** (base
  duty, Section 301, MPF, HMF) vs **excluded** (Section 232, IEEPA→CAPE, Section 122, AD/CVD). This is the
  single most date-sensitive thing in the product, surfaced up front.
- **Breakdowns:** recovery **by year** (a bar chart spanning 2021–2026), **by program** (unused-substitution
  §1313(j)(2) vs direct-identification §1313(j)(1)), and the **top HTS subheadings**.
- **Blocked / not recoverable**, grouped honestly:
  - *Recoverable with work* — **missing export proof (~$0.50M)** (get a B/L or AES ITN → moves to headline),
    **not yet liquidated (~$0.01M)**.
  - *Not recoverable as-is* — **ineligible duty (~$1.4M)**: Section 232 (no drawback) and an **IEEPA** line
    explicitly routed to the **separate CAPE track**, not drawback; **out of window**; **'other'-basket HTS**;
    **no matching import**; and **unused import duty** (duty-paid imports with no export to claim against).
- **"What we'd need to file"** checklist: obtain export proof for the matched-but-unproven exports, confirm
  liquidation, engage a licensed broker/filer to certify & transmit (the tool prepares; a human files),
  consider Accelerated Payment + a 1A bond for a ~3-week refund, and retain records 3 years from liquidation.
- **Data-quality summary:** rows parsed vs dropped, with any warnings (e.g., an unknown HTS code).

The point: a skeptical trade-compliance manager gets an instant, *correct*, conservative number with the
logic visible — no sales call, no NDA, no week of manual review.

## 2. Layer 2 — the glass box

Open the **Glass Box** tab.

- A **reconciliation badge** confirms *Headline = Σ by-program = Σ by-year* — the totals add up at every
  drill level (this is enforced by the test suite, not just claimed).
- A **filterable table of matched pairs**: import entry/line, export reference, HTS8, quantity, provision,
  per-unit designated duty, comparator, recovery, the conservative range low, and a confidence flag.
- **Click any pair** to open *"Why this is recoverable"* — the full **trace**:
  - the **rule citations** (e.g., `19 U.S.C. 1313(j)(2)`, `19 CFR 190.32(b)(1)`) in monospace,
  - the **assumption-ID chips** (e.g., `A-01 8-digit standard`, `A-03 lesser-of`, `A-10 one-claim`),
  - a **numbered computation derivation** — designated per-unit duty → HTS match → lesser-of → line recovery,
  - the **eligible-charge breakdown** and any **excluded charges** (e.g., "Section 232 excluded — not
    drawback-eligible"),
  - the **import → export → claim window** dates and the in-window check,
  - the **confidence** and an **evidence note** (a missing-proof pair is flagged "needs B/L or AES ITN before
    filing").

Pick a direct-identification pair (provision 58) and you'll see *no lesser-of cap* and the range low equal to
the point. Pick a substitution pair (provision 59) and you'll see the comparator and a wider range — the
honest expression of "would the substituted good really bear Section 301?"

No number in any total lacks a traceable basis. That is the product.

## 3. Layer 3 — filing handoff + status (stubbed, clearly marked)

Open the **Filing** tab. A prominent **"SIMULATED — not connected to CBP"** ribbon sits over everything.

- The engine has assembled **CATAIR-shaped claim(s)** — one per drawback provision present — each showing the
  provision, the grand total claimed, a **✓ valid** structural check, and a collapsible view of the
  **record-typed transmission text** (the real ACE/ABI 10/40/41/42/43/70/71/72/89/90 record structure).
- **Mock submit** writes the would-be transmission + a manifest to `filing_out/` and re-validates — it
  transmits nothing.
- A **claim lifecycle timeline** (simulated) shows the real CBP states with projected dates: transmitted →
  accepted → complete → **accelerated payment (~3 weeks)** → under review → **liquidated** (weekly Friday) →
  true-up, plus the **3-years-from-liquidation** retention deadline. The accelerated-payment projected first
  payment is highlighted.

## 4. Try your own data

Use **Upload CSVs** with two files matching `samples/imports.csv` and `samples/exports.csv` (ACE/ITRAC-like
import file + EEI/invoice-like export file). The same instant estimate appears, with data-quality issues
surfaced for any bad rows. Swapping in a real ACE export later is a clean seam — the parser and HTS reference
are the only things that change.

## 5. Verify the correctness claims

```bash
make test     # 59 tests: ground-truth (hand-computed), rule, adversarial (double-claim, out-of-window,
              # ineligible layers, missing proof, near-miss HTS, 'other'-basket), reconciliation, property
              # (recovery never exceeds the eligible pool; quantity conservation), parser, performance.
```
The optimizer itself is validated against an exhaustive brute force across hundreds of random instances.

---

*Takeaway:* the reviewer loads data, sees an instant and conservative recovery number, drills into any
claimed line and finds defensible logic with a citation, and concludes — *"that's right, and I could defend
it in an audit."* That reaction is the product.
