"""Explainability trace builder — assembles the defensible basis for one matched pair.

PRD §4.3 hard requirement: for every claimed dollar the engine emits which import line, which export
line, which rule permitted the match, what computation produced the amount, and a confidence flag.
No number appears in any total without one of these.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from drawback.models import ChargeType, DrawbackProvision, MatchBasis, Trace

# Citations per (provision, basis) — sourced from RESEARCH.md.
_CITES = {
    DrawbackProvision.J2_UNUSED_SUBSTITUTION: [
        "19 U.S.C. 1313(j)(2)", "19 CFR 190.32(b)(1)", "19 CFR 190.2 (per-unit averaging)",
    ],
    DrawbackProvision.J1_UNUSED_DIRECT: [
        "19 U.S.C. 1313(j)(1)", "19 CFR 190.51(b)",
    ],
    DrawbackProvision.B_MFG_SUBSTITUTION: [
        "19 U.S.C. 1313(b)", "19 CFR 190.22(a)(1)(ii)", "19 CFR 190.11(d)",
    ],
    DrawbackProvision.A_MFG_DIRECT: [
        "19 U.S.C. 1313(a)", "19 CFR 190.51(b)",
    ],
}
_BASIS_CITE = {
    MatchBasis.SUBSTITUTION_8_DIGIT: "19 CFR 190.2 (same 8-digit HTSUS subheading)",
    MatchBasis.SUBSTITUTION_10_DIGIT: "19 U.S.C. 1313(j)(5)(B) ('other'-basket -> 10-digit)",
    MatchBasis.DIRECT_IDENTIFICATION: "19 CFR 190.14 (identification of merchandise)",
}


def build_trace(
    *,
    provision: DrawbackProvision,
    basis: MatchBasis,
    designated_per_unit: Decimal,
    comparator_per_unit: Optional[Decimal],
    per_unit_recovery: Decimal,
    quantity: int,
    recovery: Decimal,
    eligible_charges: dict[ChargeType, Decimal],
    excluded_charges: dict[ChargeType, str],
    import_date: date,
    export_date: date,
    claim_date: date,
    within_window: bool,
    hts_match_reason: str,
    extra_flags: list[str],
) -> Trace:
    cites = list(_CITES.get(provision, [])) + [_BASIS_CITE[basis]]

    assumptions = ["A-10 (one-claim conservation)", "A-12 (eligible-charge config)", "A-16 (Decimal money)"]
    steps: list[str] = []
    steps.append(f"Designated import eligible duty per unit (per-unit averaging, 19 CFR 190.2): ${designated_per_unit:.6f}")
    if basis is MatchBasis.SUBSTITUTION_8_DIGIT:
        assumptions += ["A-01 (8-digit standard)", "A-20 (8-digit prefix)"]
    elif basis is MatchBasis.SUBSTITUTION_10_DIGIT:
        assumptions += ["A-02 ('other'->10-digit)", "A-04 (applies to (b) and (j)(2))"]
    elif basis is MatchBasis.DIRECT_IDENTIFICATION:
        assumptions += ["A-06 (direct-ID, no lesser-of)", "A-08 (190.14 identification)"]
    steps.append(f"HTS match: {hts_match_reason}")

    if comparator_per_unit is None:
        steps.append("Direct identification — no lesser-of cap; recovery = 99% x duty paid (A-06).")
        assumptions.append("A-11 (99% rate)")
    else:
        assumptions += ["A-03 (unused lesser-of)" if provision is DrawbackProvision.J2_UNUSED_SUBSTITUTION
                        else "A-05 (manufacturing lesser-of)", "A-21 (comparator rate profile)", "A-22 (range)"]
        steps.append(
            f"Comparator: duty the exported article would owe if imported = ${comparator_per_unit:.6f} per unit "
            f"(at the export HTS's eligible-charge rate profile, A-21)."
        )
        steps.append(
            f"Lesser-of: 99% x min(${designated_per_unit:.6f}, ${comparator_per_unit:.6f}) "
            f"= ${per_unit_recovery:.6f} per unit."
        )
    steps.append(f"Line recovery = ${per_unit_recovery:.6f} x {quantity} units = ${recovery:.2f} (quantized HALF_UP).")

    if not within_window:
        steps.append("OUT OF 5-YEAR WINDOW (19 USC 1313(r)) — excluded from headline (A-09).")

    flags = list(extra_flags)
    if excluded_charges:
        flags.append(
            "ineligible charges excluded from this import: "
            + ", ".join(f"{getattr(c, 'value', c)} ({reason.split('—')[0].strip()})"
                        for c, reason in excluded_charges.items())
        )

    return Trace(
        match_basis=basis,
        provision=provision,
        rule_citations=cites,
        assumption_ids=assumptions,
        computation_steps=steps,
        eligible_charges=dict(eligible_charges),
        excluded_charges=dict(excluded_charges),
        import_date=import_date,
        export_date=export_date,
        claim_date=claim_date,
        within_window=within_window,
        flags=flags,
    )
