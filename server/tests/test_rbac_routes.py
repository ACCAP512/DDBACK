"""M2 — end-to-end RBAC over the API: login, role enforcement per route, signer-only sign-off,
and tenant isolation through the HTTP layer.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from server.auth import service
from server.db import models as m
from server.db.base import Base, make_engine
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind, UserRole

_BROKER_SIGNOFF = {
    "filer_name": "Jane Broker",
    "role": "licensed_customs_broker",
    "license_number": "CB-12345",
    "accepted_defensible": True,
    "accepted_review_understood": True,
}


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAWBACK_JWT_SECRET", "test-secret-for-m2-rbac-suite-0123456789")
    engine = make_engine(f"sqlite:///{tmp_path / 'rbac.db'}")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    with TestSession() as s:
        ta = m.Tenant(name="Tenant A", kind=TenantKind.broker_firm)
        tb = m.Tenant(name="Tenant B", kind=TenantKind.broker_firm)
        s.add_all([ta, tb])
        s.flush()
        ca = m.Client(tenant_id=ta.id, name="A-Importer", importer_id="11-1111111")
        cb = m.Client(tenant_id=tb.id, name="B-Importer", importer_id="22-2222222")
        s.add_all([ca, cb])
        s.flush()
        pa = m.Program(tenant_id=ta.id, client_id=ca.id, name="pa", drawback_type=DrawbackType.j2)
        pb = m.Program(tenant_id=tb.id, client_id=cb.id, name="pb", drawback_type=DrawbackType.j2)
        s.add_all([pa, pb])
        s.flush()
        claim_a = m.Claim(
            tenant_id=ta.id, program_id=pa.id, status=ClaimStatus.draft,
            estimated_refund=Decimal("100.00"), defensible_refund=Decimal("50.00"),
        )
        claim_b = m.Claim(tenant_id=tb.id, program_id=pb.id, status=ClaimStatus.draft)
        s.add_all([claim_a, claim_b])
        s.flush()
        service.create_user(s, tenant_id=ta.id, email="signer@a.com", password="pw-signer-a",
                            name="Signer A", role=UserRole.signer)
        service.create_user(s, tenant_id=ta.id, email="prep@a.com", password="pw-prep-a",
                            name="Prep A", role=UserRole.preparer)
        service.create_user(s, tenant_id=tb.id, email="signer@b.com", password="pw-signer-b",
                            name="Signer B", role=UserRole.signer)
        s.commit()
        ids = {"claim_a": claim_a.id, "claim_b": claim_b.id, "ca": ca.id, "cb": cb.id}

    from server.api import deps
    from server.api.main import app

    def _override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[deps.get_db] = _override_get_db
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def _login(client, email, password) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_me_and_bad_password(api):
    client, _ = api
    token = _login(client, "signer@a.com", "pw-signer-a")
    me = client.get("/api/auth/me", headers=_auth(token)).json()
    assert me["role"] == "signer"
    assert "claims:sign" in me["permissions"]

    assert client.post("/api/auth/login", json={"email": "signer@a.com", "password": "nope"}).status_code == 401


def test_missing_token_is_401(api):
    client, _ = api
    assert client.get("/api/clients").status_code == 401


def test_signer_only_signoff(api):
    client, ids = api
    signer = _login(client, "signer@a.com", "pw-signer-a")
    preparer = _login(client, "prep@a.com", "pw-prep-a")

    # A preparer lacks claims:sign → 403.
    forbidden = client.post(f"/api/claims/{ids['claim_a']}/signoff", json=_BROKER_SIGNOFF, headers=_auth(preparer))
    assert forbidden.status_code == 403

    # The signer can sign → 200, recorded.
    ok = client.post(f"/api/claims/{ids['claim_a']}/signoff", json=_BROKER_SIGNOFF, headers=_auth(signer))
    assert ok.status_code == 200, ok.text
    assert ok.json()["signoff"]["signed"] is True

    detail = client.get(f"/api/claims/{ids['claim_a']}", headers=_auth(signer)).json()
    assert detail["signoff"]["filer_name"] == "Jane Broker"


def test_signoff_rejects_incomplete_attestation(api):
    client, ids = api
    signer = _login(client, "signer@a.com", "pw-signer-a")
    # licensed broker with no license number + not accepting the figures → 422 from the engine's validator
    bad = {"filer_name": "X", "role": "licensed_customs_broker", "accepted_defensible": False}
    assert client.post(f"/api/claims/{ids['claim_a']}/signoff", json=bad, headers=_auth(signer)).status_code == 422


def test_tenant_isolation_through_the_api(api):
    client, ids = api
    signer_a = _login(client, "signer@a.com", "pw-signer-a")

    # Tenant A's signer cannot read tenant B's claim — it simply doesn't exist for them.
    assert client.get(f"/api/claims/{ids['claim_b']}", headers=_auth(signer_a)).status_code == 404

    # The clients list returns only tenant A's client.
    listed = client.get("/api/clients", headers=_auth(signer_a))
    assert listed.status_code == 200
    assert {c["id"] for c in listed.json()} == {ids["ca"]}
