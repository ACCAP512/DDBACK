"""M3 — the portfolio cockpit over HTTP (BUILD_PLAN §5).

Login → GET /api/portfolio/summary and /clock: the histogram, lanes, 5-year clock, and accrued $
all reconcile; the read-only client role is refused the cross-client cockpit; and tenant isolation
holds end-to-end through the API.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from server.auth import service
from server.db import models as m
from server.db.base import Base, make_engine
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind, UserRole


def _claim(s, program, *, status, estimated=None, defensible=None, actual=None, signed=False):
    s.add(m.Claim(
        tenant_id=program.tenant_id, program_id=program.id, status=status,
        estimated_refund=None if estimated is None else Decimal(estimated),
        defensible_refund=None if defensible is None else Decimal(defensible),
        actual_refund=None if actual is None else Decimal(actual),
        signoff={"signed": True, "filer_name": "S"} if signed else None,
        filed_at=datetime.now(timezone.utc) if status in (
            ClaimStatus.filed, ClaimStatus.paid) else None,
    ))


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAWBACK_JWT_SECRET", "test-secret-for-m3-portfolio-suite-0123456789")
    engine = make_engine(f"sqlite:///{tmp_path / 'portfolio_api.db'}")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    with TestSession() as s:
        ta = m.Tenant(name="Tenant A", kind=TenantKind.broker_firm)
        tb = m.Tenant(name="Tenant B", kind=TenantKind.broker_firm)
        s.add_all([ta, tb]); s.flush()
        ca = m.Client(tenant_id=ta.id, name="A-Importer", importer_id="11-1111111")
        cb = m.Client(tenant_id=tb.id, name="B-Importer", importer_id="22-2222222")
        s.add_all([ca, cb]); s.flush()
        pa = m.Program(tenant_id=ta.id, client_id=ca.id, name="PA", drawback_type=DrawbackType.j2)
        pb = m.Program(tenant_id=tb.id, client_id=cb.id, name="PB", drawback_type=DrawbackType.j2)
        s.add_all([pa, pb]); s.flush()

        # Tenant A claims spanning the lanes.
        _claim(s, pa, status=ClaimStatus.draft, estimated="100.00", defensible="60.00")     # +exception
        _claim(s, pa, status=ClaimStatus.ready, estimated="80.00", defensible="80.00")       # awaiting
        _claim(s, pa, status=ClaimStatus.ready, estimated="50.00", defensible="50.00", signed=True)  # ready
        _claim(s, pa, status=ClaimStatus.filed, estimated="40.00", defensible="40.00")        # in-flight
        _claim(s, pa, status=ClaimStatus.paid, estimated="30.00", defensible="30.00", actual="28.00")  # realized
        # An undesignated import line for A → at-risk = full eligible duty.
        s.add(m.ImportEntryLine(
            tenant_id=ta.id, client_id=ca.id, entry_number="A-E1", line_no=1, hts10="6402999000",
            import_date=date(2024, 1, 1), quantity=100, uom="EA", entered_value=Decimal("1000.00"),
            charges={"base_duty": "100.00", "section_232": "500.00"}))  # 232 excluded

        # Tenant B — must never appear in A's cockpit.
        _claim(s, pb, status=ClaimStatus.draft, defensible="999.00")
        s.add(m.ImportEntryLine(
            tenant_id=tb.id, client_id=cb.id, entry_number="B-E1", line_no=1, hts10="6402999000",
            import_date=date(2024, 1, 1), quantity=100, uom="EA", entered_value=Decimal("1.00"),
            charges={"base_duty": "777.00"}))

        service.create_user(s, tenant_id=ta.id, email="admin@a.com", password="pw-admin-a",
                            name="Admin A", role=UserRole.admin)
        service.create_user(s, tenant_id=ta.id, email="client@a.com", password="pw-client-a",
                            name="Client A", role=UserRole.client, client_scope_id=ca.id)
        s.commit()

    from server.api import deps
    from server.api.main import app

    def _override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[deps.get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(client, email, password) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_summary_reconciles(api):
    token = _login(api, "admin@a.com", "pw-admin-a")
    body = api.get("/api/portfolio/summary", headers=_auth(token))
    assert body.status_code == 200, body.text
    data = body.json()

    # Histogram.
    assert data["by_status"]["draft"] == 1
    assert data["by_status"]["ready"] == 2
    assert data["by_status"]["filed"] == 1
    assert data["by_status"]["paid"] == 1

    # Lanes.
    lanes = {ln["key"]: ln for ln in data["lanes"]}
    assert lanes["awaiting_signoff"]["count"] == 1
    assert lanes["ready_to_file"]["count"] == 1
    assert lanes["draft"]["count"] == 1
    assert lanes["filed"]["count"] == 1
    assert lanes["exceptions"]["count"] == 1          # the draft, gap 40
    assert lanes["exceptions"]["total_defensible"] == "40.00"

    # Totals: pipeline = 60+80+50, in-flight = 40, realized = 28 (actual), at-risk = 100 (232 excluded).
    assert data["totals"]["pipeline"] == "190.00"
    assert data["totals"]["in_flight"] == "40.00"
    assert data["totals"]["realized"] == "28.00"
    assert data["totals"]["at_risk_duty"] == "100.00"
    assert data["totals"]["clients"] == 1
    assert data["totals"]["active_claims"] == 4       # all but paid

    # Accrued + clock present and self-consistent.
    assert [a["client_name"] for a in data["accrued"]] == ["A-Importer"]
    assert data["clock"]["total_at_risk_duty"] == "100.00"
    assert data["clock"]["soonest"][0]["entry_number"] == "A-E1"


def test_clock_drilldown(api):
    token = _login(api, "admin@a.com", "pw-admin-a")
    data = api.get("/api/portfolio/clock?limit=5", headers=_auth(token)).json()
    assert data["total_lines"] == 1
    assert data["soonest"][0]["at_risk_duty"] == "100.00"
    assert data["soonest"][0]["eligible_duty_paid"] == "100.00"


def test_client_role_is_refused_the_cockpit(api):
    token = _login(api, "client@a.com", "pw-client-a")
    assert api.get("/api/portfolio/summary", headers=_auth(token)).status_code == 403
    assert api.get("/api/portfolio/clock", headers=_auth(token)).status_code == 403


def test_cockpit_needs_auth(api):
    assert api.get("/api/portfolio/summary").status_code == 401
