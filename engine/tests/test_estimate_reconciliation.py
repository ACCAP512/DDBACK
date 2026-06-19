"""Reconciliation (PRD §9): headline == Σ by_program == Σ by_year == Σ by_hts == Σ headline pairs,
at every drill level; and conservatism (missing proof excluded from the headline)."""

from datetime import date
from decimal import Decimal

from _builders import exp, imp, dataset
from drawback.data.generator import generate
from drawback.estimate import build_estimate


def _sum(seq):
    return sum(seq, Decimal("0"))


def test_breakdowns_reconcile_to_headline():
    est = build_estimate(generate(scale="demo"))
    hp = est.headline_point
    assert hp == _sum(p.recovery for p in est.headline_pairs())
    assert hp == _sum(b.recovery for b in est.by_program)
    assert hp == _sum(b.recovery for b in est.by_year)
    assert hp == _sum(b.recovery for b in est.by_hts)


def test_headline_quantities_reconcile():
    est = build_estimate(generate(scale="demo"))
    hq = sum(p.quantity for p in est.headline_pairs())
    assert hq == sum(b.quantity for b in est.by_program)
    assert hq == sum(b.quantity for b in est.by_year)


def test_conservatism_missing_proof_not_in_headline():
    i = imp("APX1", "8501314000", 10, {"base_duty": 1000}, date(2024, 1, 1), value=35714)
    e = exp("E1", "8501314000", 10, 3571, date(2024, 6, 1), proof=False)
    est = build_estimate(dataset([i], [e]), claim_date=date(2025, 1, 1))
    assert est.headline_point == Decimal("0")     # nothing defensible without proof
    assert est.potential_total > 0                # surfaced as needs-review
    assert "missing_export_proof" in est.blocked_by_reason


def test_every_headline_dollar_has_a_trace():
    est = build_estimate(generate(scale="demo"))
    for p in est.headline_pairs():
        assert p.trace is not None
        assert p.trace.rule_citations           # non-empty citations
        assert p.trace.assumption_ids
        assert p.trace.computation_steps
