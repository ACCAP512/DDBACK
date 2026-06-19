# UX_RESEARCH.md — UI/UX best practices & the best fit for Drawback Engine

**Date:** 2026-06-19 · **Status:** research & recommendation (no build). Synthesizes six primary-source
research streams (financial/numeric UI; trust/explainability/uncertainty; instant-value/onboarding;
data tables/drill-down; design-system/stack/a11y; competitor teardown). Authoritative sources are
Nielsen Norman Group (NN/g), Baymard, W3C/WCAG 2.2, Google PAIR, peer-reviewed uncertainty-viz research,
IBM Carbon/Material 3/Polaris/Atlassian, and official library docs. Unsourced vendor statistics were
excluded.

---

## 0. Bottom line (the best fit, in one paragraph)

Keep the product's **distinctive, custom-designed look and its glass-box architecture — they are
strongly validated by the research** — but make five evidence-backed moves: (1) **flip the default theme
to light** for the dense numeric/audit work (dark stays as a persistent toggle); (2) **add headless
accessibility primitives** (Radix UI / React Aria) under the existing custom CSS so the drawer, menus,
and table meet **WCAG 2.2 AA** without changing the look — this matters for B2B security/procurement
review; (3) **harden the data-table** (pagination + virtualization, not infinite scroll; right-aligned
tabular numerals; faceted batch filters; a persistent "showing $Y of $X" reconciliation line); (4)
**upgrade the CSV upload** to template + fuzzy column-mapping + a green/amber/red review grid with
**explicit row accounting** ("matched 8,412 of 8,500; 88 skipped — missing HTS"); and (5) **frame
conservatism as the headline feature** ("we excluded $X to stay audit-defensible"), with itemized,
adjacent caveats rather than legalese. The single most important structural finding — *the explanation
must be the source of truth the headline is computed from, never a post-hoc narrative* — the engine
**already satisfies** (the headline IS the sum of traced pairs). That is the moat; the UI's job is to
make it visible and accessible.

---

## 1. What the current build already gets right (validated by research)

Encouraging: most of the existing design choices are exactly what the literature recommends. Don't
re-litigate these — protect them.

| Current choice | Validated by |
|---|---|
| **One hero number + low→point range bar** (magnitude as length, not color) | NN/g preattentive dashboards (position/length processed preattentively; color carries no magnitude); competitor analogs (Stripe hero-KPI, insurtech "compare your options" range). |
| **Per-row trace drawer (nonmodal side panel)** | NN/g *Data Tables* names a **nonmodal side panel the preferred pattern** for full per-row detail "while still allowing the user to view the rest of the table." Beats a modal because the auditor reads the trace *against* the row. |
| **Glass-box: every dollar traces to import→export→rule→computation→confidence** | NN/g (drill-down provenance primes verification), Google PAIR (feature-based + counterfactual explanations), Stanford credibility Guideline #1 ("make it easy to verify"). The competitor teardown found **no** rival exposes per-line math — this is the ownable wedge. |
| **Headline = exact sum of traced pairs (reconciles)** | The credit-decision research's #1 anti-pattern is *"reason-code laundering"* — computing one way, explaining another. The engine structurally avoids it; the headline renders *from* the trace. **This is the most important thing the product does right.** |
| **Monospace for HTS codes & CFR citations; tabular money** | Type/numeral guidance (tabular lining figures for financial columns); Polaris ("tabular numbers for all currency"); mono signals "exact, copyable identifier." |
| **Dated tariff-eligibility banner ("as of 2026-06-19")** | Stanford Guideline #8 (recency = credibility); Vanta/Drata "live, dated evidence"; Tariff Refund HQ as-of dating tied to regulatory events. |
| **Blocked / pending / not-recoverable surfaced, not hidden** | PAIR: hedged/limited claims *increase long-term reliance*; VSUP research: suppressing precision on shaky values makes users weight risk correctly. Conservatism is a trust-builder. |
| **"Load sample data" instant path** | PLG/onboarding: pre-populated demo data is the highest-leverage first-run pattern ("an empty product is terrifying"); ungated value before signup is the magnet. |
| **Compliance guardrail footer (not filer of record / not legal advice)** | Compliance-tool norm; non-law-firm disclaimer pattern (Tariff Refund HQ). |

---

## 2. The key decisions — options compared, with a recommendation each

### 2.1 Theme: dark vs light vs hybrid — **the biggest call**

This is the one place the research pushes *against* the current build, and the evidence is specific.

| Option | Case for | Case against | Evidence |
|---|---|---|---|
| **Dark default** (status quo) | Distinctive, "screenshot-worthy" hero; reads as a "Bloomberg/terminal" power tool; trust-research notes a dark professional aesthetic *can* be an asset. | **Light mode measures better for small dense numerals**, and the advantage **grows as text shrinks**; dark-mode **halation** hurts readers with astigmatism on exactly this text-/number-dense content; conservative B2B finance buyers skew toward "report/spreadsheet" credibility; the **exported PDF audit packet** is light, so a dark UI diverges from the artifact. | NN/g *Dark Mode vs Light Mode* (light won across acuity/proofreading; gap grows at small sizes); NN/g *Dark Mode Issues* (halation/astigmatism). |
| **Light default + persistent dark toggle** ✅ **recommended** | Best legibility for the glass-box tables and the long analytical sessions; matches the exported audit PDF; reads as credible to the skeptical compliance buyer; keeps dark available for users/marketing who prefer it. | Slightly less "distinctive" out of the gate than an all-dark hero. | NN/g recommends offering dark as a *pervasive toggle* for long-form work rather than forcing it as the default for dense reading. Most "serious money" tools (Stripe, Ramp, Mercury, compliance suites) are light by default. |
| **Hybrid** (dark marketing/hero, light app) | Keeps a striking landing while the work happens in light. | Theme switch mid-flow can feel inconsistent; more design overhead. | — |

**Recommendation: make LIGHT the default, ship dark as a persistent, token-driven toggle.** Tokenize the
theme (semantic CSS custom properties) so this is a swap, not a rewrite — which also de-risks the
decision (you can A/B it). This is the highest-uncertainty call here; the current dark is *defensible* if
it reads as audit-workpaper, but the weight of evidence favors light for this audience and content. Cheap
to defer behind tokens; don't let it block other work.

### 2.2 Number & uncertainty presentation

- **Two-tier formatting:** abbreviated low-precision at the top (`$3.79M`, or the range `$2.9M–$3.8M`);
  full precision + separators + decimal alignment in the ledger (`$3,787,133.61`). Trailing-cent
  precision on an *estimate* is the "false precision" NN/g warns against; exactness belongs in the
  auditable line items, where it *is* the credibility. (Datawrapper; NN/g.)
- **Defuse the "cliff effect."** Don't let `low → point` read as "≥low guaranteed, point = truth." Label
  semantics explicitly: *low* = "conservative floor we'd defend in audit," *point* = "best estimate on
  current evidence." Round the range to honest significant figures. (Joslyn & Savelli deterministic-
  construal error; the cliff-effect literature.)
- **Confidence = categorical (High/Med/Low) with a bound action**, shown only because it changes the
  decision: High → "include in claim," Medium → "review before filing," Low/Blocked → "excluded — resolve
  evidence to include." (Google PAIR.)
- **Value-suppress shaky numbers:** render a low-confidence row's figure in muted weight and a *coarser*
  number (`~$12K, pending`) so the UI itself resists over-reading it. (Correll/Moritz/Heer VSUP, CHI 2018.)
- **Frequency framing in copy:** "About 3 of these 10 line items are firmly recoverable; 4 are pending."
  (Hullman.)
- *(Optional, high-payoff)* a **quantile-dotplot mini-viz** of the recovery distribution in the detail
  drawer — the best-evidenced encoding for getting a non-statistician to *feel* a range without misreading
  it. (Fernandes/Kay/Hullman, CHI 2018.)

### 2.3 The glass-box trace structure

- **Exactly two disclosure levels, never three** (NN/g: users get lost past two). Level 1 = gist
  (recovery, confidence+range, import→export→claim dates, one-line plain-language basis). Level 2 =
  expandable proof (numbered computation, citations, charge breakdown, evidence manifest, assumptions),
  with **Expand-All/Collapse-All** because the auditor wants everything at once. Use **tabs, not nested
  accordions**, for the parallel dense views (computation vs citations vs evidence). Default the
  computation section **open** (the derivation *is* the trust artifact).
- **Make provenance structured, counted, and deep-linked:** show an evidence count on the row before the
  drawer opens ("4 documents, 2 verified" — the number itself primes verification, per NN/g); make each
  CFR citation a **live deep link** to the eCFR text and each line a link to its source entry/B-L.
- **Give each pair a deep-linkable URL / standalone printable page** (`/pairs/{id}`) and **prev/next
  inside the drawer** — the one thing a drawer lacks vs a page is shareability; the standalone page is the
  exportable audit artifact. (NN/g modal/nonmodal; data-lineage drill-to-source.)
- **Assumptions are correctable, first-person controls:** an INFERRED/GUESS chip the user can confirm/
  override, which recomputes and *upgrades the confidence* — turning a disclaimer into an interaction that
  visibly improves the number. (PAIR corrections; NN/g first-person hedging.)

### 2.4 Data table & drill-down (the pairs grid)

- **Pagination + virtualization, NOT infinite scroll** — infinite scroll defeats the auditor's
  find/compare/return tasks and destroys positional memory (NN/g). Default page size 25–50 (Carbon:
  paginate >25), user-settable and persisted, with a "1–50 of 1,284 pairs" landmark. Virtualize the
  rendered window for smoothness.
- **Default-sort by Recovery $ descending** (the money is the first question); server-authoritative sort
  so what's shown is what the totals were computed against.
- **Right-align all numerics on the decimal with tabular figures; units in headers**, not cells. Human-
  readable first column (import entry / pair id, not a UUID). One horizontal styling system (zebra *or*
  lines) + hover-row highlight; freeze header + identifier column on scroll. Offer a **comfortable/compact
  density toggle** (default comfortable; compact for the power auditor).
- **Faceted *batch* filters with counts** on year / HTS / program / confidence / recovery-range (compliance
  pros arrive with the whole query in mind → Apply model, not re-run-per-keystroke; don't scroll-to-top on
  change). Applied filters as removable chips. **Saved Views** (named filter+sort+columns) — highest-
  leverage feature for repeat audit work. Optional **group-by-HTS with subtotals** so the grid *is* the
  by-HTS breakdown.
- **Make reconciliation visible:** a breadcrumb drill path (`All ▸ FY2024 ▸ HTS 8501.31 ▸ Pair #1043`),
  visible total rows that sum exactly, and a persistent **"Showing $Y of $X (filtered)"** so a headline is
  never confused with a filtered subset — the most dangerous trust gap in a financial grid.

### 2.5 Instant value, onboarding & upload (the magnet)

- **Keep the estimate fully ungated** — the wow is the top-of-funnel; gating it forfeits the ~3× visitor-
  activation advantage and the screenshot virality. Promote **"Load sample data" to a primary/co-equal
  CTA**; it must drive the *identical* full dashboard + glass box (a real interactive demo, not a teaser).
  Place the first signup ask *after* the wow, at value-escalation (save / export / start filing).
- **Upgrade the CSV upload — current biggest UX gap.** Per the importer playbook (Flatfile/OneSchema/
  Dromo): a **downloadable example template per file** + one-line spec; **auto/fuzzy column mapping** the
  user *confirms* (trade files have wildly inconsistent headers); a **green/amber/red review grid** with a
  "show only problem rows" filter; and — critically for a number people act on financially — **explicit row
  accounting**: "Matched 8,412 of 8,500 import lines; 88 skipped (missing HTS) — excluded from your
  estimate." Silent row-dropping is a credibility killer; visible exclusions *increase* trust.
- **Perceived performance:** <1s → just render; 2–10s → a **full-screen skeleton of the results dashboard**
  (not a bare spinner); >10s → a **determinate progress bar** ("Analyzing 8,500 lines…"). A **short
  (~0.7s) count-up** on the headline is justified (directs attention, screenshot-friendly) *only if it
  resolves fast and isn't masking latency*; honor `prefers-reduced-motion`. (NN/g response-time limits +
  skeleton-screen research.)
- **Trust at the upload moment** (their confidential customs data is the peak-anxiety point): put
  reassurance *at the dropzone*, not the footer — "We use your import/export lines only to compute your
  estimate." If architecturally possible, lead with the strongest frame ("analyzed in your browser / not
  stored / not shared / deleted after processing" — and make it true); *non-retention/non-sharing*
  messaging beats generic "we're secure." No account to get the number is itself the biggest trust
  reducer. (Smashing/Friedman privacy-UX.)
- **No upfront product tour.** Lead with the number; let curiosity pull users deeper via dismissible,
  signal-triggered nudges ("This shipment contributes ~$Y — here's why"). Reserve linear wizard steps only
  for the eventual filing flow. (NN/g onboarding-tutorials.)

### 2.6 Stack & accessibility — the build-vs-adopt decision

The crucial framing from the research: **"component library" and "visual style" are two separable
decisions.** The trap is adopting a *styled* system to get accessibility, then fighting its look forever.
For a distinctive, data-dense, AA-critical B2B tool built by a small team, the 2024–2026 answer is
**headless behavior + your own visual layer.**

| Layer | Options | Recommendation |
|---|---|---|
| **Interactive widgets** (trace drawer, menus, combobox filters, tabs, tooltips) | Hand-rolled (status quo) · Radix UI · React Aria (Adobe) · Ark UI | **Adopt Radix UI** (or React Aria) headless primitives. They ship WAI-ARIA, focus trap/restore, ESC-to-close, roving tabindex, keyboard nav — *unstyled*, so the custom look is 100% preserved. These are exactly the widgets a small team silently ships AA bugs on (a hand-rolled focus-trapping drawer is the #1 risk). |
| **Data table** | Hand-rolled · TanStack Table v8 (headless engine) · React Aria Table | **TanStack Table v8** for sort/filter/group/virtualize logic under your own markup (keeps the look); or **React Aria Table** if you want table-specific a11y (multi-select, column-resize, expandable rows) built in. |
| **Styling** | Custom CSS + tokens (status quo) · Tailwind · CSS-in-JS | **Keep hand-written CSS, formalize into semantic design tokens** (primitive → semantic CSS custom properties; theming = re-point tokens). Zero-runtime, maximally distinctive, validated by 2024–26 consensus (runtime CSS-in-JS is out; Mantine itself moved off Emotion). Adopt Tailwind *only* if you also adopt shadcn/ui (they're a package deal). |
| **Charts** | Hand-rolled SVG (status quo) · Recharts v3 · visx · Nivo | **Two defensible paths.** (A) Keep hand-rolled SVG (smallest bundle, most distinctive) **+ commit to the chart-a11y checklist** (text/data-table fallback, 3:1 non-text contrast, redundant color, reduced-motion). (B) **Adopt Recharts v3** — its `accessibilityLayer` is **on by default** (keyboard + ARIA) for ~50kB gz, removing a11y maintenance. For a trust-critical tool facing procurement review, **(B) is the safer default**; choose (A) only if a designer actively owns the chart a11y. |
| **Avoid** | MUI/Ant/Carbon/Atlassian (styled enterprise systems); runtime CSS-in-JS (Chakra/Emotion) | Skip unless a procurement mandate for a *named* WCAG-mapped system overrides distinctiveness — they impose a recognizable identity you'd fight, and MUI's good data grid is paid. |

**Why accessibility is not optional here:** **WCAG 2.2 became a W3C Recommendation on 2024-12-12.**
Enterprise buyers increasingly gate purchases on a **VPAT/ACR + WCAG conformance**, and a skeptical
professional reads broken keyboard nav / low contrast as "not enterprise-ready" — directly undermining the
*trust* the product sells. The criteria that bite this UI: **1.4.3** text contrast 4.5:1, **1.4.11**
non-text contrast 3:1 (chart bars, status chips, the range bar — the one charts fail most), **1.4.1** use
of color (status needs color **+** icon/label), **2.1.1/2.1.2** keyboard + no focus trap (the drawer must
release focus), **2.4.11** focus not obscured by sticky headers, **2.5.8** target size ≥24px (dense row
actions), **1.3.1/4.1.2** semantic tables with `aria-sort`. Headless primitives + Recharts v3 get a small
team most of the way to AA with the least custom code.

---

## 3. The one principle that defines the product

From the credit-decision and explainable-AI research: **the explanation must be a first-class output of
the calculation, never a narrative back-fitted to an opaque score** (the CFPB-named "reason-code
laundering" anti-pattern). The headline must render *from* the same trace that justifies each dollar — if
the explanation and the math could ever diverge, the glass box is fake. **The engine already enforces this**
(the headline is literally the sum of traced, rule-cited pairs). Every UI decision should protect this
invariant: no displayed number without a trace, every aggregate decomposable to the line, reconciliation
made visible. This — not the visual theme — is the durable differentiator the competitor teardown confirms
nobody else has.

---

## 4. Prioritized recommendations (ranked by impact ÷ effort)

**Tier 1 — high impact, do first**
1. **Add headless a11y primitives (Radix/React Aria) under the existing CSS** + run the WCAG 2.2 AA
   checklist (contrast, keyboard, focus, target size, redundant status encoding). Closes the procurement/
   trust gap without changing the look.
2. **Upgrade the CSV upload**: template downloads + fuzzy column mapping + green/amber/red review grid +
   **explicit "matched X of Y, skipped Z" accounting**. Biggest UX gap today; directly protects the
   credibility of the number.
3. **Harden the pairs table**: pagination + virtualization, right-aligned tabular numerals, faceted batch
   filters with chips, Saved Views, and a persistent **"Showing $Y of $X (filtered)"** reconciliation line
   + breadcrumb drill path.
4. **Make conservatism the headline**: a persistent "We excluded $X to stay audit-defensible (N items
   pending)" line; itemized, plain-language, *adjacent* caveats instead of legalese; confidence tiers with
   bound actions; value-suppressed styling on shaky figures.

**Tier 2 — medium**
5. **Tokenize the theme and flip the default to light** (dark as persistent toggle); align the exported
   PDF audit packet to the light view.
6. **Two-tier number formatting** (abbreviated hero/tiles, full-precision ledger) + range-label semantics
   that defuse the cliff effect + frequency framing in copy.
7. **Trace polish**: two-level disclosure with Expand-All, tabs for parallel views, deep-linkable
   `/pairs/{id}` standalone printable page, prev/next in the drawer, live eCFR/source deep links, evidence
   counts on rows.
8. **Onboarding**: promote "Load sample data" to primary; full-screen skeleton during compute; dropzone
   privacy/non-retention reassurance; signal-triggered nudges instead of a tour.

**Tier 3 — polish / optional**
9. Correctable assumption chips that recompute confidence.
10. Quantile-dotplot mini-viz of the recovery distribution in the drawer.
11. Charting decision (keep hand-SVG + a11y checklist, or move to Recharts v3).

---

## 5. Source index (load-bearing, by stream)

**Financial/numeric UI:** NN/g [Dashboards/preattentive](https://www.nngroup.com/articles/dashboards-preattentive/),
[Complex apps](https://www.nngroup.com/articles/complex-application-design/),
[Dark vs Light](https://www.nngroup.com/articles/dark-mode/),
[Dark-mode issues](https://www.nngroup.com/articles/dark-mode-users-issues/) ·
W3C WCAG [1.4.3](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) /
[1.4.11](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html) /
[1.4.1](https://www.w3.org/TR/UNDERSTANDING-WCAG20/visual-audio-contrast-without-color.html) ·
IBM Carbon [data-viz color](https://carbondesignsystem.com/data-visualization/color-palettes/) ·
[A List Apart — tables](https://alistapart.com/article/web-typography-tables/) ·
[Datawrapper number formats](https://www.datawrapper.de/academy/custom-number-formats-that-you-can-display-in-datawrapper) ·
[Colour Blind Awareness](https://www.colourblindawareness.org/colour-blindness/types-of-colour-blindness/).

**Trust / explainability / uncertainty:** [Google PAIR — Explainability + Trust](https://pair.withgoogle.com/chapter/explainability-trust/) ·
NN/g [AI Hallucinations](https://www.nngroup.com/articles/ai-hallucinations/),
[Smarts over Sentience](https://www.nngroup.com/articles/smarts-emotion-trust-ai/),
[Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) ·
[Stanford Web Credibility](https://en.wikipedia.org/wiki/Stanford_Web_Credibility_Project) ·
[Fernandes/Kay/Hullman — quantile dotplots, CHI 2018](https://dl.acm.org/doi/10.1145/3173574.3173718) ·
[Correll/Moritz/Heer — VSUP, CHI 2018](https://dl.acm.org/doi/pdf/10.1145/3173574.3174216) ·
[Joslyn & Savelli — deterministic construal](https://www.semanticscholar.org/paper/Visualizing-Uncertainty-for-Non-Expert-End-Users%3A-Joslyn-Savelli/36b2a28c641278c3761610a10d804e0e5dad9d5b).

**Instant value / onboarding / upload:** [OpenView/Poyar PLG benchmarks](https://openviewpartners.com/blog/your-guide-to-product-led-growth-benchmarks/) ·
NN/g [Response-time limits](https://www.nngroup.com/articles/response-times-3-important-limits/),
[Skeleton screens](https://www.nngroup.com/articles/skeleton-screens/),
[Onboarding vs contextual help](https://www.nngroup.com/articles/onboarding-tutorials/) ·
[Flatfile](https://flatfile.com/blog/optimizing-csv-import-experiences-flatfile-portal/) ·
[Dromo — silent CSV failures](https://dromo.io/blog/common-data-import-errors-and-how-to-fix-them) ·
[Smashing/Friedman — privacy UX](https://www.smashingmagazine.com/2019/04/privacy-concerns-ux-web-forms/).

**Tables / drill-down:** NN/g [Data Tables](https://www.nngroup.com/articles/data-tables/),
[Modal & Nonmodal Dialogs](https://www.nngroup.com/articles/modal-nonmodal-dialog/),
[Accordions](https://www.nngroup.com/articles/accordions-on-desktop/),
[Infinite Scroll](https://www.nngroup.com/articles/infinite-scrolling-tips/),
[Breadcrumbs](https://www.nngroup.com/articles/breadcrumbs/),
[Filters vs Facets](https://www.nngroup.com/articles/filters-vs-facets/) ·
[Carbon Pagination](https://carbondesignsystem.com/components/pagination/usage/) ·
[Material 3 Density](https://m3.material.io/foundations/layout/understanding-layout/density).

**Stack / a11y:** [W3C WCAG 2.2 (Rec 2024-12-12)](https://www.w3.org/TR/WCAG22/) ·
[Radix Primitives](https://www.radix-ui.com/primitives) · [React Aria](https://react-aria.adobe.com/) ·
[TanStack Table](https://tanstack.com/table/latest) ·
[Recharts v3 migration (accessibilityLayer)](https://github.com/recharts/recharts/wiki/3.0-migration-guide) ·
[Inwald — React design systems 2025](https://inwald.com/2025/11/modern-design-systems-for-react-in-2025-a-pragmatic-comparison/).

**Competitor teardown:** [Flexport duty drawback](https://www.flexport.com/products/duty-drawback/) ·
[Tariff Refund HQ](https://www.tariffrefundhq.com/) · [Zollback](https://www.zollback.com/) ·
[Vanta Trust Center](https://www.vanta.com/products/trust-center) ·
[CFPB — adverse-action AI notices](https://www.consumerfinance.gov/about-us/blog/innovation-spotlight-providing-adverse-action-notices-when-using-ai-ml-models/).

> Source-quality caveat: NN/g, WCAG, PAIR, and the peer-reviewed uncertainty-viz papers are the most
> rigorous and load-bearing. PLG funnel percentages and competitor marketing claims are directional
> (practitioner/vendor sources), not controlled studies. Live competitor calculators were read from page
> copy, not exercised end-to-end.
