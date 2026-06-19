"""Ground-truth fixtures: tiny datasets with hand-computed recovery the engine must match exactly."""

from datetime import date
from decimal import Decimal

from _builders import exp, imp
from drawback.data.hts_reference import DEFAULT_REFERENCE as REF
from drawback.matching.engine import match
from drawback.models import DrawbackProvision


def test_substitution_lesser_of_ground_truth():
    # 10 DC motors; eligible duty per unit = 282.714; substitution, comparator == designated -> full.
    i = imp("APX1", "8501314000", 10,
            {"base_duty": 280, "section_301": 2500, "section_232": 1000, "mpf": 34.64, "hmf": 12.50},
            date(2024, 1, 15), value=10000)
    e = exp("E1", "8501314000", 10, 1000, date(2024, 6, 1))  # no direct link -> (j)(2)
    res = match([i], [e], date(2024, 9, 1), REF)

    assert len(res.pairs) == 1
    p = res.pairs[0]
    assert p.provision is DrawbackProvision.J2_UNUSED_SUBSTITUTION
    assert p.quantity == 10
    assert p.recovery == Decimal("2798.87")     # 0.99 * 282.714 * 10
    assert p.recovery_low == Decimal("323.87")  # 0.99 * 32.714 * 10 (no speculative 301)
    assert p.in_headline is True
    assert res.eligible_duty_pool == Decimal("2827.14")
    assert res.ineligible_total == Decimal("1000")  # the 232


def test_direct_identification_beats_substitution():
    # Same import, but the export is the SAME goods (direct-ID) at a LOWER value. Direct-ID has no
    # lesser-of cap -> recovers the full duty, more than substitution would.
    i = imp("APX1", "8501314000", 10,
            {"base_duty": 280, "section_301": 2500, "mpf": 34.64, "hmf": 12.50},
            date(2024, 1, 15), value=10000)
    e = exp("E1", "8501314000", 10, 100, date(2024, 6, 1), direct_entry="APX1", direct_line=1)
    res = match([i], [e], date(2024, 9, 1), REF)

    p = res.pairs[0]
    assert p.provision is DrawbackProvision.J1_UNUSED_DIRECT
    assert p.per_unit_comparator_duty is None          # no cap
    assert p.recovery == Decimal("2798.87")            # 0.99 * 282.714 * 10
    assert p.recovery_low == p.recovery                # no range collapse for direct-ID


def test_partial_export_quantity():
    # import 100 units of duty, export only 40 -> recover on 40 only.
    i = imp("APX1", "8504409500", 100, {"base_duty": 1500, "section_301": 25000, "mpf": 346.4, "hmf": 125},
            date(2024, 1, 1), value=100000)
    e = exp("E1", "8504409500", 40, 1000, date(2024, 8, 1), direct_entry="APX1", direct_line=1)
    res = match([i], [e], date(2025, 1, 1), REF)
    p = res.pairs[0]
    assert p.quantity == 40
    # eligible per unit = (1500+25000+346.4+125)/100 = 269.714 ; 0.99*269.714*40 = 10680.6744 -> 10680.67
    assert p.recovery == Decimal("10680.67")
