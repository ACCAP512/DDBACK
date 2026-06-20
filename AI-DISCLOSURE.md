# AI-Assisted Development Disclosure

*Diligence exhibit (per docs/COMPLIANCE.md §3). This documents the AI tooling used to build the
Software so a buyer can confirm clean, assignable title. It is factual disclosure, not legal advice.*

## Tooling
- The Software was built **solo** by the copyright holder (single author; no employees, contractors, or
  co-authors — confirmed by the git history) with substantial assistance from an **AI coding assistant
  (Anthropic's Claude / Claude Code)** acting under the developer's direction.
- **Output ownership:** Anthropic's commercial terms **assign output ownership to the user** — *"you own
  the Outputs… Anthropic hereby assigns to you all of Anthropic's right, title, and interest, if any, in
  and to the Outputs."* Anthropic retains no ownership of the generated code. Retain the version of those
  terms in force during development as a closing exhibit.
- No other AI code-generation tool was used. No third-party AI vendor holds any interest in the Software.

## Human authorship (why the work is copyrightable and assignable)
U.S. law requires human authorship (*Thaler v. Perlmutter*, D.C. Cir. 2025; cert. denied 2026), and the
U.S. Copyright Office's January 2025 *Copyrightability* report confirms that **AI-*assisted* work is
copyrightable where there is sufficient human creative selection, coordination, arrangement, and
modification.** That standard is met here; the evidentiary record is in the repo:
- **Direction:** the build followed a written PRD and a Phase-0 research gate; architecture and design
  decisions (the pure-stdlib-core constraint, the exact min-cost-max-flow optimizer, the rule taxonomy,
  the layer structure, the headline/defensibility partition) were made by the human author and are
  recorded in `docs/DECISIONS.md` and `docs/PLAN.md`.
- **Substance:** the legal rules were rebuilt from primary sources by the author and tagged
  `[VERIFIED]/[INFERRED]/[GUESS]` in `docs/RESEARCH.md` and `docs/ASSUMPTIONS.md`.
- **Review/iteration:** the running log in `docs/PROGRESS.md` and the commit history evidence
  human review, integration, and modification of generated output.

## Honest limitation (disclose, do not hide)
Individual purely-machine-generated, trivial, unedited fragments may carry thin or no copyright (as
boilerplate does regardless of AI). This does **not** impair ownership or transfer of the work as a whole:
the **selection/coordination/arrangement (the compilation) is protectable**, the **legal-logic encoding is
a protectable trade secret**, and the moat rests substantially on domain correctness, the validated engine,
and ongoing maintenance — not on locking up every literal line. The seller should disclose (not conceal)
the AI assistance and represent that all resulting IP is owned by the seller and that the AI tool's terms
were complied with.

## Recommended representations for an asset sale (for counsel to paper)
- Ownership/title; non-infringement; **no employer/contractor claim** (built solo, **not employed during
  development** — confirmed); OSS-disclosure schedule (see `THIRD-PARTY-NOTICES.md` / `sbom.json`); an
  **AI-tools-used disclosure** (this file); a **public-domain-content** rep (the encoded law is public
  domain — 17 U.S.C. 105; *Georgia v. Public.Resource.Org*); and a **synthetic-data/no-PII** rep (all
  bundled data is synthetic — no customer or personal data travels with the asset).
