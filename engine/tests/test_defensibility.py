"""Correctness hardening (COMPLIANCE.md §4 P6). Proves the structural guarantees:
  B6 — no [INFERRED]/[GUESS] legal rule can contribute a dollar to the defensible headline;
  B7 — the 99%/lesser-of caps and the claimed≤duty-paid invariant RAISE on violation (never clamp);
  B9 — a per-claim defensibility report is produced, validatable from the trace alone.
"""

import dataclasses
from decimal import Decimal

import pytest

from drawback import assumptions as A
from drawback.data.generator import generate
from drawback.defensibility import CENT, ReconciliationError, harden
from drawback.estimate import build_estimate


# ── B6: the defensible headline depends ONLY on [VERIFIED] legal rules ──────────
def test_defensible_pairs_are_all_verified():
    res = harden(build_estimate(generate(scale="demo")))
    assert res.defensible_headline > 0
    for pd in res.pairs:
        if pd.defensible > 0:
            assert pd.basis_all_verified and not pd.blocking_rules


def test_structural_guarantee_flipping_a_rule_to_inferred_removes_its_dollars(monkeypatch):
    """If any legal basis rule were [INFERRED], its claims must drop OUT of the defensible headline —
    enforced structurally, not by convention. A-03 (unused lesser-of) is in every substitution pair."""
    est = build_estimate(generate(scale="demo"))
    base = harden(est)
    monkeypatch.setitem(A.REGISTRY, "A-03", dataclasses.replace(A.REGISTRY["A-03"], tag=A.Tag.INFERRED))
    flipped = harden(est)
    assert flipped.defensible_headline < base.defensible_headline  # substitution dollars dropped
    for pd in flipped.pairs:
        if "A-03" in pd.basis_rules:
            assert pd.defensible == 0 and "A-03" in pd.blocking_rules


def test_defensible_is_the_verified_only_floor_at_or_below_headline_low():
    """The defensible headline is AT MOST the engine's conservative floor (headline_low), and STRICTLY
    below it when some headline pairs touch an INFERRED legal rule (here, the 'other'-basket inference
    A-04) — those correctly route to needs-review per B6. Every excluded headline pair has a documented
    blocking rule (the hardening never excludes silently)."""
    est = build_estimate(generate(scale="demo"))
    res = harden(est)
    assert res.defensible_headline <= est.headline_low
    assert res.defensible_headline <= res.best_estimate == est.headline_point
    for pd in res.pairs:
        if pd.in_headline and pd.defensible == 0:
            assert pd.blocking_rules, "a headline pair excluded from defensible must have a blocking rule"
            for rid in pd.blocking_rules:
                assert A.REGISTRY[rid].tag is not A.Tag.VERIFIED


# ── B7: reconciliation invariant RAISES on violation, never clamps ──────────────
def test_99pct_cap_violation_raises():
    est = build_estimate(generate(scale="demo"))
    est.matched_pairs[0].recovery = est.matched_pairs[0].recovery + Decimal("1000000")
    with pytest.raises(ReconciliationError):
        harden(est, strict=True)
    res = harden(est, strict=False)  # non-strict records but does not raise
    assert res.reconciliation_ok is False and res.violations


def test_lesser_of_cap_violation_raises():
    est = build_estimate(generate(scale="demo"))
    sub = next(p for p in est.matched_pairs if p.per_unit_comparator_duty is not None)
    sub.recovery = sub.recovery + Decimal("500000")
    with pytest.raises(ReconciliationError):
        harden(est, strict=True)


@pytest.mark.parametrize("seed", [1, 42, 2024])
def test_claimed_never_exceeds_duty_paid(seed):
    res = harden(build_estimate(generate(seed=seed, scale="demo")))
    assert res.reconciliation_ok
    assert res.total_claimed <= res.duty_paid_on_claimed + CENT
    assert res.defensible_headline <= res.best_estimate


# ── B9: the per-claim defensibility report, validatable from the trace alone ────
def test_report_is_self_contained_and_consistent():
    res = harden(build_estimate(generate(scale="demo")))
    r = res.report()
    assert r["reconciliation"]["ok"] is True
    assert r["defensible_headline"] == float(round(res.defensible_headline, 2))
    assert r["rules_fired"] and all({"citations", "tier", "contributes_to"} <= x.keys() for x in r["rules_fired"])
    # every rule contributing to the defensible headline is VERIFIED (B6, visible in the report)
    assert all(x["tier"] == "VERIFIED" for x in r["rules_fired"] if x["contributes_to"] == "defensible")
    assert r["claim_lines"] and "disclaimer" in r
    # claim-line defensible amounts sum to the headline
    s = round(sum(cl["defensible"] for cl in r["claim_lines"]), 2)
    assert s == float(round(res.defensible_headline, 2))
