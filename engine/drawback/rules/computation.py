"""Refund computation: the 99% rate, per-unit averaging, and the "lesser of" cap.

Citations: 19 CFR 190.51(b) (99%), 190.2 (per-unit averaging), 190.32(b) (unused-substitution
lesser-of), 190.22(a)(1)(ii) (manufacturing-substitution lesser-of), 190.11. RESEARCH Q3/Q5.
Assumptions: A-03, A-05, A-06, A-11, A-16, A-21.

CORRECTNESS NOTES
- Money is Decimal; per-unit values keep full precision, line totals quantize to cents HALF_UP (A-16).
- The two substitution comparators DIFFER and never share a path:
    unused (j)(2):        min( import duty paid ,  duty the EXPORTED article would owe if imported )
    manufacturing (b):    min( import duty paid ,  duty the SUBSTITUTED INPUT would owe if imported )
- The comparator is built at the export HTS's *eligible-charge rate profile* (A-21). The realistic
  point estimate includes Section 301 where the HTS is 301-listed; the conservative low end excludes
  speculative 301 — this is what drives the headline range (FR1.4), not false precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from drawback.config import tariff_eligibility as elig
from drawback.models import CENTS, ZERO, ChargeType
from drawback.rules.hts import hts8

DRAWBACK_RATE = Decimal("0.99")  # 19 CFR 190.51(b) — 99% for (a)/(b)/(c)/(j) provisions (A-11)


def quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# Designated import side — per-unit eligible duty (per-unit averaging, 190.2)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class EligibleDuty:
    per_unit: Decimal                              # eligible duty/taxes/fees per imported unit
    total_eligible: Decimal
    eligible_charges: dict[ChargeType, Decimal]    # charge -> amount included
    excluded_charges: dict[ChargeType, str]        # charge -> reason excluded


def eligible_per_unit_duty(charges: dict[ChargeType, Decimal], quantity: int) -> EligibleDuty:
    """Apportion the eligible charges on an entry-summary line equally across its units (190.2).

    A charge is included only if ``config.tariff_eligibility`` says so as of the config date (A-12);
    everything else (232/IEEPA/122/AD-CVD/unknown) is excluded WITH a reason for the trace.
    """
    eligible: dict[ChargeType, Decimal] = {}
    excluded: dict[ChargeType, str] = {}
    for charge, amount in charges.items():
        if amount == ZERO:
            continue
        if elig.is_eligible(charge):
            eligible[charge] = amount
        else:
            excluded[charge] = elig.note(charge)
    total = sum(eligible.values(), ZERO)
    per_unit = (total / Decimal(quantity)) if quantity > 0 else ZERO
    return EligibleDuty(per_unit=per_unit, total_eligible=total,
                        eligible_charges=eligible, excluded_charges=excluded)


# ─────────────────────────────────────────────────────────────────────────────
# Comparator side — duty the exported/substituted article would owe "if imported" (190.32(b)(1)(ii))
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Comparator:
    per_unit: Decimal
    breakdown: dict[str, Decimal] = field(default_factory=dict)


def comparator_per_unit_duty(
    export_hts10: str,
    value_per_unit: Decimal,
    ref,
    include_speculative_301: bool = True,
) -> Comparator:
    """Hypothetical per-unit duty on the exported article if it were imported, at the export HTS's
    eligible-charge rate profile (A-21), applied to its per-unit value at the port of export.

    ``ref`` (drawback.data.hts_reference) supplies the ad-valorem rates:
        ref.base_duty_rate(hts8) -> Decimal     (e.g. 0.025 for 2.5%)
        ref.section_301_rate(hts8) -> Decimal   (0 if the HTS is not 301-listed)
        ref.mpf_rate(), ref.hmf_rate() -> Decimal
    """
    h8 = hts8(export_hts10)
    bd = {}
    base = ref.base_duty_rate(h8) * value_per_unit
    if base > 0:
        bd[ChargeType.BASE_DUTY.value] = base
    if include_speculative_301:
        s301 = ref.section_301_rate(h8) * value_per_unit
        if s301 > 0:
            bd[ChargeType.SECTION_301.value] = s301
    mpf = ref.mpf_rate() * value_per_unit
    hmf = ref.hmf_rate() * value_per_unit
    if mpf > 0:
        bd[ChargeType.MPF.value] = mpf
    if hmf > 0:
        bd[ChargeType.HMF.value] = hmf
    return Comparator(per_unit=sum(bd.values(), ZERO), breakdown=bd)


# ─────────────────────────────────────────────────────────────────────────────
# Per-unit recovery (the lesser-of + 99%)
# ─────────────────────────────────────────────────────────────────────────────
def unused_substitution_per_unit(designated_per_unit: Decimal, comparator_per_unit: Decimal) -> Decimal:
    """1313(j)(2): 99% x min(import duty paid, duty the EXPORTED article would owe if imported)."""
    return DRAWBACK_RATE * min(designated_per_unit, comparator_per_unit)


def manufacturing_substitution_per_unit(designated_per_unit: Decimal, input_comparator_per_unit: Decimal) -> Decimal:
    """1313(b): 99% x min(import duty paid, duty the SUBSTITUTED INPUT would owe if imported) (A-05)."""
    return DRAWBACK_RATE * min(designated_per_unit, input_comparator_per_unit)


def direct_identification_per_unit(designated_per_unit: Decimal) -> Decimal:
    """1313(j)(1)/(a): 99% x duty paid on the identified imported units — no lesser-of cap (A-06)."""
    return DRAWBACK_RATE * designated_per_unit


def apply_recovered_materials(per_unit_recovery: Decimal, recovered_value_per_unit: Decimal) -> Decimal:
    """Destruction (190.32(b)(2)/190.71(d)): reduce recovery by the recovered-materials value.

    Conservative approximation (A-03 note): deduct 99% of the recovered value per unit, clamped at 0.
    Recovered value is 0 for ordinary exports, so this rarely binds for the electronics persona.
    """
    if recovered_value_per_unit <= ZERO:
        return per_unit_recovery
    reduced = per_unit_recovery - DRAWBACK_RATE * recovered_value_per_unit
    return reduced if reduced > ZERO else ZERO


def line_recovery(per_unit_recovery: Decimal, quantity: int) -> Decimal:
    """Quantize the line total to cents (A-16)."""
    return quantize_money(per_unit_recovery * Decimal(quantity))
