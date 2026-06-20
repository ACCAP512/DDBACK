"""M3 — portfolio rollups for the work-queue home (BUILD_PLAN §5).

Covers the status histogram, the triage lanes (the ``ready`` split on sign-off, the CBP-RFI lane,
the cross-cutting exceptions lane, ``paid`` excluded from work), per-client accrued $, and isolation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest
from sqlalchemy.orm import Session, sessionmaker

from server.auth.context import Principal
from server.db import models as m
from server.db import scoping
from server.db.base import Base, make_engine
from server.domain import portfolio
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind, UserRole


@pytest.fixture()
def Smk(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'portfolio.db'}")
    Base.metadata.create_all(eng)
    yield sessionmaker(bind=eng, expire_on_commit=False, class_=Session)
    eng.dispose()


def _scoped(Smk, tenant_id: str) -> Session:
    s = Smk()
    scoping.bind_principal(s, Principal(user_id="u", tenant_id=tenant_id, role=UserRole.admin,
                                        client_scope_id=None))
    return s


def _client(s, tenant_id, name) -> m.Client:
    c = m.Client(tenant_id=tenant_id, name=name, importer_id="11-1111111")
    s.add(c); s.flush()
    return c


def _program(s, client) -> m.Program:
    p = m.Program(tenant_id=client.tenant_id, client_id=client.id, name=f"{client.name}-prog",
                  drawback_type=DrawbackType.j2)
    s.add(p); s.flush()
    return p


def _claim(s, program, *, status, estimated=None, defensible=None, actual=None,
           signed=False) -> m.Claim:
    c = m.Claim(
        tenant_id=program.tenant_id, program_id=program.id, status=status,
        estimated_refund=None if estimated is None else Decimal(estimated),
        defensible_refund=None if defensible is None else Decimal(defensible),
        actual_refund=None if actual is None else Decimal(actual),
        signoff={"signed": True, "filer_name": "S"} if signed else None,
        filed_at=datetime.now(timezone.utc) if status in (
            ClaimStatus.filed, ClaimStatus.under_review, ClaimStatus.liquidated, ClaimStatus.paid) else None,
    )
    s.add(c); s.flush()
    return c


# ── status histogram ──────────────────────────────────────────────────────────
def test_claims_by_status_zero_filled(Smk):
    w = Smk()
    t = m.Tenant(name="T", kind=TenantKind.broker_firm); w.add(t); w.flush()
    p = _program(w, _client(w, t.id, "C"))
    _claim(w, p, status=ClaimStatus.draft)
    _claim(w, p, status=ClaimStatus.draft)
    _claim(w, p, status=ClaimStatus.paid, actual="100.00")
    tid = t.id
    w.commit(); w.close()

    s = _scoped(Smk, tid)
    counts = portfolio.claims_by_status(s)
    assert counts["draft"] == 2
    assert counts["paid"] == 1
    assert counts["filed"] == 0  # present, zero-filled
    assert set(counts) == {s.value for s in ClaimStatus}


# ── lanes ─────────────────────────────────────────────────────────────────────
def test_lanes_split_ready_on_signoff_and_flag_exceptions(Smk):
    w = Smk()
    t = m.Tenant(name="T", kind=TenantKind.broker_firm); w.add(t); w.flush()
    p = _program(w, _client(w, t.id, "C"))
    # ready + unsigned → awaiting_signoff; and a gap (est>def) → also an exception
    _claim(w, p, status=ClaimStatus.ready, estimated="100.00", defensible="60.00", signed=False)
    # ready + signed → ready_to_file (no gap)
    _claim(w, p, status=ClaimStatus.ready, estimated="80.00", defensible="80.00", signed=True)
    # under_review → cbp_rfi
    _claim(w, p, status=ClaimStatus.under_review, estimated="50.00", defensible="50.00")
    # draft with a gap → draft lane + exception
    _claim(w, p, status=ClaimStatus.draft, estimated="40.00", defensible="10.00")
    # paid → no work lane
    _claim(w, p, status=ClaimStatus.paid, estimated="30.00", defensible="30.00", actual="30.00")
    tid = t.id
    w.commit(); w.close()

    s = _scoped(Smk, tid)
    lanes = {ln.key: ln for ln in portfolio.lanes(s)}
    assert lanes["awaiting_signoff"].count == 1
    assert lanes["ready_to_file"].count == 1
    assert lanes["cbp_rfi"].count == 1
    assert lanes["draft"].count == 1
    assert lanes["filed"].count == 0
    # exceptions: the ready-unsigned (gap 40) and the draft (gap 30) — paid/ready-signed excluded
    assert lanes["exceptions"].count == 2
    assert lanes["exceptions"].total_defensible == Decimal("70.00")  # 40 + 30 gaps
    # the biggest-gap exception previews first
    assert lanes["exceptions"].preview[0].gap == Decimal("40.00")
    # the awaiting-sign-off lane holds its defensible value
    assert lanes["awaiting_signoff"].total_defensible == Decimal("60.00")


# ── per-client accrued ────────────────────────────────────────────────────────
def test_per_client_accrued_buckets_and_includes_zero_claim_clients(Smk):
    w = Smk()
    t = m.Tenant(name="T", kind=TenantKind.broker_firm); w.add(t); w.flush()
    busy = _client(w, t.id, "Busy")
    idle = _client(w, t.id, "Idle")  # no claims — must still appear
    p = _program(w, busy)
    _claim(w, p, status=ClaimStatus.draft, defensible="100.00")      # pipeline
    _claim(w, p, status=ClaimStatus.ready, defensible="50.00")       # pipeline
    _claim(w, p, status=ClaimStatus.filed, defensible="200.00")      # in-flight
    _claim(w, p, status=ClaimStatus.liquidated, defensible="40.00")  # in-flight
    _claim(w, p, status=ClaimStatus.paid, defensible="60.00", actual="58.00")  # realized (actual)
    tid = t.id
    w.commit(); w.close()

    s = _scoped(Smk, tid)
    accrued = {a.client_name: a for a in portfolio.per_client_accrued(s)}
    assert accrued["Busy"].pipeline == Decimal("150.00")    # 100 + 50
    assert accrued["Busy"].in_flight == Decimal("240.00")   # 200 + 40
    assert accrued["Busy"].realized == Decimal("58.00")     # actual, not defensible
    assert accrued["Busy"].claims_total == 5
    # zero-claim client present and all-zero
    assert accrued["Idle"].claims_total == 0
    assert accrued["Idle"].pipeline == accrued["Idle"].in_flight == accrued["Idle"].realized == Decimal("0.00")


# ── tenant isolation ──────────────────────────────────────────────────────────
def test_portfolio_is_tenant_isolated(Smk):
    w = Smk()
    ta = m.Tenant(name="A", kind=TenantKind.broker_firm)
    tb = m.Tenant(name="B", kind=TenantKind.broker_firm)
    w.add_all([ta, tb]); w.flush()
    _claim(w, _program(w, _client(w, ta.id, "A-imp")), status=ClaimStatus.draft, defensible="11.00")
    _claim(w, _program(w, _client(w, tb.id, "B-imp")), status=ClaimStatus.draft, defensible="99.00")
    tenant_a = ta.id
    w.commit(); w.close()

    s = _scoped(Smk, tenant_a)
    assert portfolio.claims_by_status(s)["draft"] == 1
    accrued = portfolio.per_client_accrued(s)
    assert len(accrued) == 1
    assert accrued[0].client_name == "A-imp"
    assert accrued[0].pipeline == Decimal("11.00")  # never sees B's 99
