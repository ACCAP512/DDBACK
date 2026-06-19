"""Layer 3 (stubbed): CATAIR claim build/validate/mock-submit and lifecycle simulation."""

from datetime import date
from decimal import Decimal

from drawback.data.generator import generate
from drawback.estimate import build_estimate
from drawback.filing.catair import build_claims, mock_submit, validate_claim
from drawback.filing.lifecycle import simulate_lifecycle


def _charges_by_key(ds):
    return {(im.entry_number, im.line_number): im.charges for im in ds.imports}


def test_build_and_validate_claims():
    ds = generate(scale="demo")
    est = build_estimate(ds)
    claims = build_claims(est, import_charges_by_key=_charges_by_key(ds))
    assert claims, "should produce at least one claim (one per provision)"
    for c in claims:
        assert validate_claim(c) == [], f"claim {c.claim_number} invalid: {validate_claim(c)}"
        # totals reconcile to the grand total
        acct_sum = round(sum(c.totals["by_accounting_class"].values()), 2)
        assert abs(acct_sum - c.totals["grand_total_claimed"]) <= 0.05
        assert c.simulated is True


def test_claims_total_reconciles_to_headline():
    ds = generate(scale="demo")
    est = build_estimate(ds)
    claims = build_claims(est, import_charges_by_key=_charges_by_key(ds))
    claimed = round(sum(c.totals["grand_total_claimed"] for c in claims), 2)
    assert abs(claimed - float(round(est.headline_point, 2))) <= 0.10  # apportionment rounding tolerance


def test_mock_submit_writes_and_validates(tmp_path):
    ds = generate(scale="demo")
    est = build_estimate(ds)
    claims = build_claims(est, import_charges_by_key=_charges_by_key(ds))
    manifest = mock_submit(claims, tmp_path)
    assert manifest["simulated"] is True
    assert all(c["valid"] for c in manifest["claims"])
    assert (tmp_path / "manifest.json").exists()
    assert list(tmp_path.glob("*.catair.txt"))


def test_lifecycle_accelerated_payment_timing():
    lc = simulate_lifecycle(date(2026, 6, 19), accelerated_payment=True, estimated_amount=Decimal("100000"))
    assert lc["simulated"] is True
    states = [s["state"] for s in lc["steps"]]
    assert "accelerated_payment_paid" in states
    assert "liquidated" in states
    assert lc["projected_first_payment"] < lc["retention_deadline"]
