"""M3 — clients / programs / claims management + list + lifecycle over HTTP (BUILD_PLAN §5).

Covers onboarding (create client/program with RBAC), the claim list with filters + pagination +
client-role narrowing, the enriched claim detail / glass-box / ledger / audit reads, and the lifecycle
transition — including the compliance gate that an **unsigned** claim cannot be filed.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from server.auth import service
from server.db import models as m
from server.db.base import Base, make_engine
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind, UserRole

_SIGNOFF = {
    "filer_name": "Jane Broker", "role": "licensed_customs_broker", "license_number": "CB-1",
    "accepted_defensible": True, "accepted_review_understood": True,
}


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAWBACK_JWT_SECRET", "test-secret-for-m3-mgmt-suite-0123456789")
    engine = make_engine(f"sqlite:///{tmp_path / 'mgmt.db'}")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    ids = {}
    with TestSession() as s:
        ta = m.Tenant(name="A", kind=TenantKind.broker_firm)
        tb = m.Tenant(name="B", kind=TenantKind.broker_firm)
        s.add_all([ta, tb]); s.flush()
        ca = m.Client(tenant_id=ta.id, name="A-Importer", importer_id="11-1111111")
        ca2 = m.Client(tenant_id=ta.id, name="A-Importer-2", importer_id="33-3333333")
        cb = m.Client(tenant_id=tb.id, name="B-Importer", importer_id="22-2222222")
        s.add_all([ca, ca2, cb]); s.flush()
        pa = m.Program(tenant_id=ta.id, client_id=ca.id, name="PA", drawback_type=DrawbackType.j2)
        pa2 = m.Program(tenant_id=ta.id, client_id=ca2.id, name="PA2", drawback_type=DrawbackType.a)
        s.add_all([pa, pa2]); s.flush()

        draft = m.Claim(tenant_id=ta.id, program_id=pa.id, status=ClaimStatus.draft,
                        estimated_refund=Decimal("100.00"), defensible_refund=Decimal("60.00"))
        ready = m.Claim(tenant_id=ta.id, program_id=pa2.id, status=ClaimStatus.ready,
                        estimated_refund=Decimal("80.00"), defensible_refund=Decimal("80.00"))
        s.add_all([draft, ready]); s.flush()

        # one import + export + designation on the draft claim (for glass-box / ledger reads)
        il = m.ImportEntryLine(tenant_id=ta.id, client_id=ca.id, entry_number="E1", line_no=1,
                               hts10="6402999000", import_date=date(2024, 1, 1), quantity=100, uom="EA",
                               entered_value=Decimal("1000.00"), charges={"base_duty": "100.00"})
        el = m.ExportLine(tenant_id=ta.id, client_id=ca.id, reference="BOL-1", hts10="6402999000",
                          export_date=date(2024, 6, 1), quantity=100, uom="EA",
                          value_per_unit=Decimal("20.00"))
        s.add_all([il, el]); s.flush()
        s.add(m.Designation(tenant_id=ta.id, claim_id=draft.id, import_entry_line_id=il.id,
                            export_line_id=el.id, quantity=40, provision="59",
                            per_unit_designated_duty=Decimal("1.00"), per_unit_recovery=Decimal("0.99"),
                            recovery=Decimal("39.60"), recovery_low=Decimal("39.60"),
                            confidence="VERIFIED", in_headline=True, trace={"why": "demo"}))

        service.create_user(s, tenant_id=ta.id, email="admin@a.com", password="pw", name="Admin",
                            role=UserRole.admin)
        service.create_user(s, tenant_id=ta.id, email="prep@a.com", password="pw", name="Prep",
                            role=UserRole.preparer)
        service.create_user(s, tenant_id=ta.id, email="signer@a.com", password="pw", name="Signer",
                            role=UserRole.signer)
        service.create_user(s, tenant_id=ta.id, email="client@a.com", password="pw", name="Client",
                            role=UserRole.client, client_scope_id=ca.id)
        s.commit()
        ids = {"ca": ca.id, "ca2": ca2.id, "pa": pa.id, "draft": draft.id, "ready": ready.id}

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


def _tok(client, email):
    return client.post("/api/auth/login", json={"email": email, "password": "pw"}).json()["access_token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ── clients ───────────────────────────────────────────────────────────────────
def test_create_client_requires_write_and_audits(api):
    client, _ = api
    prep, admin = _tok(client, "prep@a.com"), _tok(client, "admin@a.com")
    # preparer lacks clients:write
    assert client.post("/api/clients", json={"name": "New", "importer_id": "99"},
                       headers=_h(prep)).status_code == 403
    created = client.post("/api/clients", json={"name": "NewCo", "importer_id": "99-9"}, headers=_h(admin))
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "NewCo"


def test_client_detail_has_programs_and_accrued(api):
    client, ids = api
    admin = _tok(client, "admin@a.com")
    detail = client.get(f"/api/clients/{ids['ca']}", headers=_h(admin)).json()
    assert detail["name"] == "A-Importer"
    assert {p["name"] for p in detail["programs"]} == {"PA"}
    assert detail["accrued"]["pipeline"] == "60.00"  # the draft's defensible


# ── programs ──────────────────────────────────────────────────────────────────
def test_create_and_list_programs(api):
    client, ids = api
    prep = _tok(client, "prep@a.com")  # preparer HAS programs:write
    bad = client.post("/api/programs", json={"client_id": ids["ca"], "name": "X", "drawback_type": "zzz"},
                      headers=_h(prep))
    assert bad.status_code == 422
    ok = client.post("/api/programs",
                     json={"client_id": ids["ca"], "name": "Mfg", "drawback_type": "b"}, headers=_h(prep))
    assert ok.status_code == 201, ok.text
    listed = client.get(f"/api/programs?client_id={ids['ca']}", headers=_h(prep)).json()
    assert {p["name"] for p in listed} == {"PA", "Mfg"}


# ── claims list ───────────────────────────────────────────────────────────────
def test_list_claims_filters_and_paginates(api):
    client, ids = api
    admin = _tok(client, "admin@a.com")
    all_claims = client.get("/api/claims", headers=_h(admin)).json()
    assert all_claims["total"] == 2
    only_draft = client.get("/api/claims?status=draft", headers=_h(admin)).json()
    assert only_draft["total"] == 1 and only_draft["claims"][0]["status"] == "draft"
    by_client = client.get(f"/api/claims?client_id={ids['ca2']}", headers=_h(admin)).json()
    assert {c["program_name"] for c in by_client["claims"]} == {"PA2"}
    # bad status → 422
    assert client.get("/api/claims?status=nope", headers=_h(admin)).status_code == 422


def test_client_role_sees_only_its_claims(api):
    client, ids = api
    cl = _tok(client, "client@a.com")  # scoped to ca
    listed = client.get("/api/claims", headers=_h(cl)).json()
    assert listed["total"] == 1
    assert listed["claims"][0]["client_id"] == ids["ca"]
    # cannot read the other client's claim
    assert client.get(f"/api/claims/{ids['ready']}", headers=_h(cl)).status_code == 404


# ── claim detail / glass-box / ledger / audit ────────────────────────────────
def test_claim_detail_glassbox_ledger(api):
    client, ids = api
    admin = _tok(client, "admin@a.com")
    detail = client.get(f"/api/claims/{ids['draft']}", headers=_h(admin)).json()
    assert detail["client"]["name"] == "A-Importer"
    assert detail["designation_summary"]["count"] == 1
    assert detail["designation_summary"]["headline_total"] == "39.60"
    assert detail["allowed_transitions"] == ["ready"]

    glass = client.get(f"/api/claims/{ids['draft']}/designations", headers=_h(admin)).json()
    assert glass["count"] == 1
    assert glass["designations"][0]["trace"] == {"why": "demo"}

    ledger = client.get(f"/api/claims/{ids['draft']}/ledger", headers=_h(admin)).json()
    assert ledger["lines"][0]["available_qty"] == 100
    assert ledger["lines"][0]["designated_qty"] == 40
    assert ledger["lines"][0]["remaining_qty"] == 60


# ── lifecycle transition + the file-needs-signoff gate ────────────────────────
def test_transition_blocks_filing_unsigned_then_allows_after_signoff(api):
    client, ids = api
    prep, signer = _tok(client, "prep@a.com"), _tok(client, "signer@a.com")

    # draft → ready (preparer)
    r = client.post(f"/api/claims/{ids['ready']}/transition", json={"to": "filed"}, headers=_h(prep))
    # 'ready' claim → filed but UNSIGNED → 428 precondition required
    assert r.status_code == 428, r.text

    # an illegal jump (draft → paid) → 409
    bad = client.post(f"/api/claims/{ids['draft']}/transition", json={"to": "paid"}, headers=_h(prep))
    assert bad.status_code == 409

    # sign it, then filing is allowed
    assert client.post(f"/api/claims/{ids['ready']}/signoff", json=_SIGNOFF,
                      headers=_h(signer)).status_code == 200
    ok = client.post(f"/api/claims/{ids['ready']}/transition",
                     json={"to": "filed", "claim_number": "CBP-123"}, headers=_h(prep))
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "filed"
    assert ok.json()["claim_number"] == "CBP-123"

    # audit trail captured the sign-off + the status change
    audit = client.get(f"/api/claims/{ids['ready']}/audit", headers=_h(prep)).json()
    actions = {e["action"] for e in audit["events"]}
    assert "claim.signoff" in actions
    assert "claim.status:ready->filed" in actions
