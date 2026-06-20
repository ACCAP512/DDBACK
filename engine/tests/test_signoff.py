"""Licensed-filer sign-off gate (COMPLIANCE §4 P3): no claim is final/submitted without a lawful-filer
attestation; the attestation requires a license for brokers/attorneys and affirmative acceptance."""

import sys
from pathlib import Path

import pytest

from drawback.filing.signoff import FilerAttestation, FilerRole, SignoffError, record, validate

_ROOT = Path(__file__).resolve().parents[2]


def _att(**kw):
    base = dict(filer_name="Jane Broker", role=FilerRole.LICENSED_CUSTOMS_BROKER,
               attested_on="2026-06-19T00:00:00Z", license_number="CHB-12345",
               accepted_defensible=True)
    base.update(kw)
    return FilerAttestation(**base)


def test_valid_broker_attestation():
    rec = record(_att())
    assert rec["signed"] is True and rec["role"] == "licensed_customs_broker"


def test_broker_requires_license():
    with pytest.raises(SignoffError):
        record(_att(license_number=""))


def test_must_accept_figures():
    with pytest.raises(SignoffError):
        record(_att(accepted_defensible=False))


def test_self_filer_needs_no_license():
    rec = record(_att(role=FilerRole.SELF_FILER_OWN_ACCOUNT, license_number=""))
    assert rec["role"] == "self_filer_own_account"


def test_missing_name():
    assert "filer_name is required" in validate(_att(filer_name="  "))


# ── API gate flow ──────────────────────────────────────────────────────────────
def test_api_submit_blocked_until_signoff():
    sys.path.insert(0, str(_ROOT / "api"))
    from fastapi.testclient import TestClient
    from api.main import app
    c = TestClient(app)
    token = c.post("/api/estimate/sample").json()["token"]

    # submit before sign-off -> 428 Precondition Required
    assert c.post(f"/api/claims/{token}/submit").status_code == 428

    # invalid sign-off (broker without license) -> 422
    bad = c.post(f"/api/claims/{token}/signoff",
                 json={"filer_name": "Jane", "role": "licensed_customs_broker", "accepted_defensible": True})
    assert bad.status_code == 422

    # valid sign-off -> 200
    ok = c.post(f"/api/claims/{token}/signoff",
                json={"filer_name": "Jane Broker", "role": "licensed_customs_broker",
                      "license_number": "CHB-12345", "accepted_defensible": True})
    assert ok.status_code == 200 and ok.json()["signed"] is True

    # now submit succeeds and the attestation travels with the manifest
    sub = c.post(f"/api/claims/{token}/submit")
    assert sub.status_code == 200
    assert sub.json()["signoff"]["filer_name"] == "Jane Broker"
