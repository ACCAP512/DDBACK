"""First-class registry of the engine's legal/technical assumptions (mirrors docs/ASSUMPTIONS.md).

Glass-box principle: the engine is the source of truth for which assumptions each claimed dollar
depends on and whether they are [VERIFIED] (traced to primary law), [INFERRED] (defensibly derived,
not stated verbatim), or [GUESS] (conservative interpretation). The trace emits assumption ids; this
registry supplies their tag + plain-language summary so the UI can render honest badges and surface the
ONE assumption a user can actually resolve from their own knowledge — A-21, whether a substituted
exported good would bear Section 301 if imported.

Keep in sync with docs/ASSUMPTIONS.md. ``tests/test_assumptions.py`` checks that every assumption id
referenced by a generated trace exists here with a valid tag.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Tag(str, Enum):
    VERIFIED = "VERIFIED"   # traced to a primary source in RESEARCH.md
    INFERRED = "INFERRED"   # defensibly derived from primary sources, not stated verbatim
    GUESS = "GUESS"         # conservative interpretation where research could not confirm


@dataclass(frozen=True)
class Correction:
    """For a user-correctable assumption: what confirming / overriding it does to the number."""
    prompt: str
    confirm_label: str
    confirm_effect: str       # human description of what confirming does
    override_label: str
    override_effect: str


@dataclass(frozen=True)
class Assumption:
    id: str
    tag: Tag
    title: str
    summary: str
    correctable: bool = False
    correction: Optional[Correction] = None


# A-21 is the only assumption a claimant can resolve from facts they know (the origin/eligibility of the
# substituted exported goods). Confirming it firms the headline; overriding it drops to the floor.
_A21_CORRECTION = Correction(
    prompt="Would the substituted exported merchandise bear Section 301 if it were imported? "
           "(For example, it is the same Chinese-origin goods you imported.)",
    confirm_label="Confirm — substituted exports are Section-301-eligible",
    confirm_effect="Resolves the substitution comparator in favor of the best estimate: the conservative "
                   "floor rises to the point estimate and the headline becomes firm (range collapses).",
    override_label="Override — substituted exports are NOT Section-301-eligible (e.g., domestic origin)",
    override_effect="Caps the substitution comparator without Section 301: the headline drops to the "
                    "conservative floor; the speculative-301 portion is no longer claimed.",
)


def _a(id, tag, title, summary, correctable=False, correction=None) -> Assumption:
    return Assumption(id, tag, title, summary, correctable, correction)


REGISTRY: dict[str, Assumption] = {a.id: a for a in [
    _a("A-01", Tag.VERIFIED, "8-digit substitution standard",
       "Substitution requires the same 8-digit HTSUS subheading (1313(b)/(j)(2); 19 CFR 190.2)."),
    _a("A-02", Tag.VERIFIED, "'Other'-basket → 10-digit",
       "If the 8-digit description begins with 'other', substitution needs a 10-digit match that does not (1313(j)(5))."),
    _a("A-03", Tag.VERIFIED, "Unused-substitution lesser-of",
       "Refund = 99% × min(import duty paid, duty the exported article would owe if imported) (190.32(b)(1))."),
    _a("A-04", Tag.INFERRED, "'Other' rule applies to (b) too",
       "The 'other'→10-digit rule is applied to manufacturing 1313(b) as well as unused 1313(j)(2) (shared 190.2 definition)."),
    _a("A-05", Tag.VERIFIED, "Manufacturing-substitution lesser-of",
       "1313(b) compares against the substituted INPUT's duty, not the exported article (190.22(a)(1)(ii))."),
    _a("A-06", Tag.VERIFIED, "Direct-ID, no cap",
       "1313(j)(1)/(a) refund = 99% of duties paid on identified units; no lesser-of comparator."),
    _a("A-07", Tag.VERIFIED, "Excise double-drawback cap not applied",
       "The substituted-excise cap was judicially invalidated (NAM v. Treasury, Fed. Cir. 2021)."),
    _a("A-08", Tag.VERIFIED, "190.14 methods = direct-ID only",
       "FIFO/LIFO/low-to-high apply to direct identification; substitution uses 8-digit HTS + per-unit averaging."),
    _a("A-09", Tag.VERIFIED, "5-year window",
       "Claim within 5 years of import; export after import, before claim, within window; else excluded (1313(r))."),
    _a("A-10", Tag.VERIFIED, "One-claim conservation",
       "Each exported unit anchors at most one claim; each import's duty is designated at most once (1313(v))."),
    _a("A-11", Tag.VERIFIED, "99% rate",
       "Drawback is 99% of each eligible charge for (a)/(b)/(c)/(j) provisions (190.51(b))."),
    _a("A-12", Tag.VERIFIED, "Eligible-charge config",
       "Eligible: base duty, Section 301, MPF, HMF, importation excise. Excluded: 232, IEEPA, 122, AD/CVD."),
    _a("A-13", Tag.VERIFIED, "IEEPA → CAPE, not drawback",
       "IEEPA duties were struck down (SCOTUS 2026-02-20); refunded via CAPE, never counted as drawback."),
    _a("A-14", Tag.INFERRED, "Finally liquidated",
       "A line is headline-eligible only if its entry is treated as finally liquidated; unknown → excluded."),
    _a("A-15", Tag.VERIFIED, "Export proof required",
       "A matched pair without acceptable export proof is computed but demoted to potential (190.72)."),
    _a("A-16", Tag.INFERRED, "Decimal money",
       "Money in decimal.Decimal; per-unit averaging = line duty ÷ HTSUS quantity; quantize cents HALF_UP."),
    _a("A-17", Tag.VERIFIED, "Decision-support only",
       "The engine prepares and estimates; it is not the filer of record and not legal advice (190.6)."),
    _a("A-18", Tag.VERIFIED, "Retention from liquidation",
       "Recordkeeping/lifecycle key off the liquidation date (3 years from liquidation), not payment."),
    _a("A-19", Tag.VERIFIED, "Export need not be duty-paid",
       "Substituted merchandise may be domestic; the refunded duty is always the designated import's."),
    _a("A-20", Tag.VERIFIED, "8-digit prefix",
       "Substitution compares digits 1–8 of the 10-digit code; the statistical suffix is ignored for substitution."),
    _a("A-21", Tag.INFERRED, "Comparator rate profile (Section 301)",
       "The lesser-of comparator is computed at the export HTS's eligible-charge rate profile, INCLUDING "
       "Section 301 where the HTS is 301-listed. Whether a given substituted export would truly bear 301 "
       "depends on facts only the claimant knows — so it is surfaced as the headline range.",
       correctable=True, correction=_A21_CORRECTION),
    _a("A-22", Tag.INFERRED, "Headline range",
       "headline_point uses the realistic comparator (301 in); headline_low excludes speculative 301. "
       "The optimizer maximizes the point; the low end is the defensible floor. Resolved by A-21."),
    _a("A-23", Tag.INFERRED, "Two-pass headline/potential",
       "Pass 1 (headline) = liquidated imports × proof-backed in-window exports; Pass 2 = potential on residuals."),
]}


def get(assumption_id: str) -> Optional[Assumption]:
    """Look up by id; accepts raw ids ('A-21') or trace strings ('A-21 (comparator rate profile)')."""
    key = assumption_id.strip().split()[0].split("(")[0].strip() if assumption_id else ""
    return REGISTRY.get(key)


def registry_summary() -> dict:
    """Machine-readable registry for the API/UI."""
    out = []
    for a in REGISTRY.values():
        row = {"id": a.id, "tag": a.tag.value, "title": a.title, "summary": a.summary,
               "correctable": a.correctable}
        if a.correction:
            c = a.correction
            row["correction"] = {
                "prompt": c.prompt, "confirm_label": c.confirm_label, "confirm_effect": c.confirm_effect,
                "override_label": c.override_label, "override_effect": c.override_effect,
            }
        out.append(row)
    return {"count": len(out), "assumptions": out}
