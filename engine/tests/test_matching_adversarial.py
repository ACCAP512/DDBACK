"""Adversarial fixtures engineered to tempt wrong answers (PRD §9). The engine must exclude the right
amounts and explain why."""

from datetime import date
from decimal import Decimal

from _builders import exp, imp
from drawback.data.hts_reference import DEFAULT_REFERENCE as REF
from drawback.matching.engine import match
from drawback.models import BlockedReason, Confidence


def _reasons(res):
    return {b.reason for b in res.blocked}


def test_double_claim_is_structurally_impossible():
    # ONE import of 10 duty-paid units; TWO exports of 10 each. At most 10 units of duty can be claimed.
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2024, 1, 1), value=35714)
    e1 = exp("E1", "8501314000", 10, 3571, date(2024, 3, 1), direct_entry="APX1", direct_line=1)
    e2 = exp("E2", "8501314000", 10, 3571, date(2024, 4, 1), direct_entry="APX1", direct_line=1)
    res = match([i], [e1, e2], date(2025, 1, 1), REF)

    total_qty = sum(p.quantity for p in res.pairs)
    assert total_qty <= 10  # conservation (A-10): cannot claim more than imported
    total_rec = sum((p.recovery for p in res.pairs), Decimal("0"))
    assert total_rec <= Decimal("0.99") * Decimal("1000")  # <= 99% of the duty actually paid


def test_out_of_window_excluded():
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2018, 1, 1), value=35714)
    e = exp("E1", "8501314000", 10, 3571, date(2024, 1, 1))  # 2018 + 5yr < 2024 -> out of window
    res = match([i], [e], date(2024, 6, 1), REF)
    assert all(not p.in_headline for p in res.pairs)
    assert BlockedReason.OUT_OF_WINDOW in _reasons(res)


def test_ineligible_duty_only_yields_no_recovery():
    i = imp("APX1", "8501314000", 10, {"section_232": 1000, "ieepa": 500}, date(2024, 1, 1), value=6000)
    e = exp("E1", "8501314000", 10, 600, date(2024, 6, 1))
    res = match([i], [e], date(2025, 1, 1), REF)
    assert all(p.recovery == 0 or not p.in_headline for p in res.pairs)
    assert res.ineligible_total == Decimal("1000")  # 232 only (IEEPA tracked separately)
    assert res.ieepa_total == Decimal("500")
    assert any(b.reason is BlockedReason.INELIGIBLE_DUTY_ONLY for b in res.blocked)


def test_missing_proof_demoted_to_potential():
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2024, 1, 1), value=35714)
    e = exp("E1", "8501314000", 10, 3571, date(2024, 6, 1), proof=False)
    res = match([i], [e], date(2025, 1, 1), REF)
    assert len(res.pairs) == 1
    p = res.pairs[0]
    assert p.in_headline is False
    assert p.confidence is Confidence.LOW
    assert any("missing_export_proof" in f for f in p.trace.flags)


def test_near_miss_hts_no_match():
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2024, 1, 1), value=35714)
    e = exp("E1", "8504409500", 10, 3571, date(2024, 6, 1))  # different 8-digit subheading
    res = match([i], [e], date(2025, 1, 1), REF)
    assert res.pairs == []
    assert BlockedReason.NO_HTS_MATCH in _reasons(res)


def test_other_basket_unsubstitutable_blocked():
    # 73269086 with 10-digit suffix 88 -> 10-digit also 'other' -> no substitution at all.
    i = imp("APX1", "7326908688", 10, {"base_duty": 1000}, date(2024, 1, 1), value=10000)
    e = exp("E1", "7326908688", 10, 1000, date(2024, 6, 1))
    res = match([i], [e], date(2025, 1, 1), REF)
    assert res.pairs == []
    assert BlockedReason.OTHER_BASKET_NO_MATCH in _reasons(res)


def test_not_liquidated_import_not_in_headline():
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2024, 1, 1), value=35714, liquidated=False)
    e = exp("E1", "8501314000", 10, 3571, date(2024, 6, 1), direct_entry="APX1", direct_line=1)
    res = match([i], [e], date(2025, 1, 1), REF)
    assert len(res.pairs) == 1
    assert res.pairs[0].in_headline is False
    assert any("not_finally_liquidated" in f for f in res.pairs[0].trace.flags)
