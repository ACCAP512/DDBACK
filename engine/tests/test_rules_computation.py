"""Computation rules: per-unit averaging, 99%, lesser-of, fee eligibility — hand-computed (A-03/05/06/11)."""

from decimal import Decimal

from drawback.data.hts_reference import DEFAULT_REFERENCE as REF
from drawback.models import ChargeType
from drawback.rules import computation as comp


def test_eligible_per_unit_excludes_ineligible_charges():
    charges = {
        ChargeType.BASE_DUTY: Decimal("280"), ChargeType.SECTION_301: Decimal("2500"),
        ChargeType.SECTION_232: Decimal("1000"),  # excluded
        ChargeType.IEEPA: Decimal("500"),          # excluded
        ChargeType.MPF: Decimal("34.64"), ChargeType.HMF: Decimal("12.50"),
    }
    ed = comp.eligible_per_unit_duty(charges, 10)
    # eligible = 280 + 2500 + 34.64 + 12.50 = 2827.14 ; per unit = 282.714
    assert ed.total_eligible == Decimal("2827.14")
    assert ed.per_unit == Decimal("282.714")
    assert ChargeType.SECTION_232 in ed.excluded_charges
    assert ChargeType.IEEPA in ed.excluded_charges
    assert ChargeType.BASE_DUTY in ed.eligible_charges


def test_comparator_includes_301_when_point_excludes_when_low():
    # 85013140: base 2.8% + 301 25% + mpf .3464% + hmf .125% on $1000.
    point = comp.comparator_per_unit_duty("8501314000", Decimal("1000"), REF, include_speculative_301=True)
    low = comp.comparator_per_unit_duty("8501314000", Decimal("1000"), REF, include_speculative_301=False)
    assert point.per_unit == Decimal("282.714")   # 28 + 250 + 3.464 + 1.25
    assert low.per_unit == Decimal("32.714")       # 28 + 3.464 + 1.25 (no 301)


def test_unused_substitution_lesser_of_binds_on_comparator():
    # designated duty 282.714/unit, comparator 32.714/unit -> min = 32.714, x 0.99
    pu = comp.unused_substitution_per_unit(Decimal("282.714"), Decimal("32.714"))
    assert pu == Decimal("0.99") * Decimal("32.714")


def test_direct_identification_no_cap():
    pu = comp.direct_identification_per_unit(Decimal("282.714"))
    assert pu == Decimal("0.99") * Decimal("282.714")


def test_line_recovery_quantizes_to_cents():
    pu = comp.unused_substitution_per_unit(Decimal("282.714"), Decimal("282.714"))
    assert comp.line_recovery(pu, 10) == Decimal("2798.87")  # 0.99*282.714*10 = 2798.8686 -> 2798.87


def test_recovered_materials_reduces_destruction_recovery():
    base = comp.direct_identification_per_unit(Decimal("100"))   # 99
    reduced = comp.apply_recovered_materials(base, Decimal("50"))  # 99 - 0.99*50 = 49.5
    assert reduced == Decimal("49.50")
    assert comp.apply_recovered_materials(base, Decimal("1000")) == Decimal("0")  # clamped
