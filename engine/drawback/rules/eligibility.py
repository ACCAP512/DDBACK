"""Eligibility gating predicates: which imports are worth designating, and which matched pairs are
defensible enough for the *headline* number vs. surfaced as *potential — needs review* (D-008).

Citations: 19 CFR 190.3(a) (finally-liquidated, eligible charges), 190.51(a)(1)/190.72 (export proof).
Assumptions: A-12 (eligible charges), A-14 (liquidation), A-15 (proof), A-19 (export need not be duty-paid).

The headline/potential split is driven by PROOF + WINDOW + LIQUIDATION + data quality — NOT by the
comparator inference (A-21), whose uncertainty is expressed through the headline *range* instead. That
keeps the headline meaningful: a fully proof-backed, in-window, liquidated, 8-digit-or-direct match is
HIGH-confidence headline recovery.
"""

from __future__ import annotations

from drawback.config import tariff_eligibility as elig
from drawback.models import BlockedReason, Confidence, ImportLine


def has_eligible_duty(line: ImportLine) -> bool:
    """True if the import line carries any drawback-eligible charge (A-12). Lines with only
    232/IEEPA/122/AD-CVD contribute nothing to drawback and are surfaced as blocked elsewhere."""
    return any(elig.is_eligible(c) and amt > 0 for c, amt in line.charges.items())


def is_headline_import(line: ImportLine) -> bool:
    """A designated import qualifies for the *headline* pass only if it has eligible duty AND is
    treated as finally liquidated (A-14). Not-liquidated imports fall to the potential pass."""
    return has_eligible_duty(line) and line.liquidated


def pair_confidence(
    has_proof: bool, in_window: bool, liquidated: bool
) -> tuple[Confidence, bool, list[str]]:
    """Classify a feasible matched pair. Returns (confidence, in_headline, flags).

    Order matters — the most disqualifying condition wins, and each is conservative (fails out of the
    headline rather than into it)."""
    if not in_window:
        return Confidence.LOW, False, ["out_of_window (19 USC 1313(r); A-09)"]
    if not has_proof:
        return Confidence.LOW, False, ["missing_export_proof (19 CFR 190.72; A-15)"]
    if not liquidated:
        return Confidence.MEDIUM, False, ["import_not_finally_liquidated (19 CFR 190.3(a); A-14)"]
    return Confidence.HIGH, True, []


def export_block_reason(has_proof: bool, in_window: bool) -> BlockedReason:
    if not in_window:
        return BlockedReason.OUT_OF_WINDOW
    if not has_proof:
        return BlockedReason.MISSING_EXPORT_PROOF
    return BlockedReason.NO_HTS_MATCH
