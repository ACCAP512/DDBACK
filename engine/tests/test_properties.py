"""Property tests across generated datasets (PRD §9): the engine must never violate conservation or
exceed the eligible duty pool, for any seed."""

from decimal import Decimal

import pytest

from drawback.config.tariff_eligibility import AS_OF
from drawback.data.generator import generate
from drawback.data.hts_reference import DEFAULT_REFERENCE
from drawback.estimate import build_estimate
from drawback.matching.engine import match


@pytest.mark.parametrize("seed", [1, 7, 42, 99, 2024])
def test_recovery_never_exceeds_eligible_pool(seed):
    ds = generate(seed=seed, scale="demo")
    est = build_estimate(ds)
    total = sum((p.recovery for p in est.matched_pairs), Decimal("0"))
    # every pair recovers <= 99% of its import's eligible duty share, so the total <= the pool.
    assert total <= est.eligible_duty_pool
    assert est.headline_low <= est.headline_point <= est.eligible_duty_pool


@pytest.mark.parametrize("seed", [1, 7, 42, 99, 2024])
def test_quantity_conservation(seed):
    ds = generate(seed=seed, scale="demo")
    res = match(ds.imports, ds.exports, AS_OF, DEFAULT_REFERENCE)

    imp_qty = {(im.entry_number, im.line_number): im.quantity for im in ds.imports}
    exp_qty = {ex.reference: ex.quantity for ex in ds.exports}
    used_imp: dict = {}
    used_exp: dict = {}
    for p in res.pairs:
        used_imp[(p.import_entry, p.import_line_no)] = used_imp.get((p.import_entry, p.import_line_no), 0) + p.quantity
        used_exp[p.export_reference] = used_exp.get(p.export_reference, 0) + p.quantity

    for k, q in used_imp.items():
        assert q <= imp_qty[k], f"import {k} over-designated: {q} > {imp_qty[k]}"
    for r, q in used_exp.items():
        assert q <= exp_qty[r], f"export {r} over-claimed: {q} > {exp_qty[r]}"


@pytest.mark.parametrize("seed", [3, 11, 50])
def test_more_exports_never_decrease_recovery(seed):
    """Monotonicity: adding exports cannot reduce total recoverable duty."""
    ds = generate(seed=seed, scale="demo")
    base = build_estimate(ds).headline_point
    # duplicate a handful of proof-backed exports (more opportunity to claim) -> recovery shouldn't drop
    extra = [e for e in ds.exports if e.has_export_proof][:10]
    for k, e in enumerate(extra):
        e2 = type(e)(**{**e.__dict__})
        e2.reference = e.reference + f"-dup{k}"
        ds.exports.append(e2)
    after = build_estimate(ds).headline_point
    assert after >= base
