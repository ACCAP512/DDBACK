"""M2 — structural tenant isolation at the data-access layer.

Proves the ``do_orm_execute`` filter (``server.db.scoping``) makes even a *naive* ``select(Model)``
return only the bound principal's tenant — no route discipline required.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from server.auth.context import Principal
from server.db import models as m
from server.db import scoping
from server.domain.enums import DrawbackType, TenantKind, UserRole


def _seed_two_tenants(SessionLocal):
    """Create two tenants, each with a client + program + claim. Returns id maps."""
    with SessionLocal() as s:
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
        cla = m.Claim(tenant_id=ta.id, program_id=pa.id)
        clb = m.Claim(tenant_id=tb.id, program_id=pb.id)
        s.add_all([cla, clb])
        s.commit()
        return {
            "ta": ta.id, "tb": tb.id, "ca": ca.id, "cb": cb.id, "cla": cla.id, "clb": clb.id,
        }


@pytest.fixture()
def SessionLocal(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def test_scoped_session_sees_only_its_tenant(SessionLocal):
    ids = _seed_two_tenants(SessionLocal)

    with SessionLocal() as s:
        scoping.bind_principal(s, Principal(user_id="ua", tenant_id=ids["ta"], role=UserRole.admin))
        # A naive select is filtered to tenant A — clients, claims, and a cross-tenant get() all obey it.
        assert {c.id for c in s.scalars(select(m.Client)).all()} == {ids["ca"]}
        assert {c.id for c in s.scalars(select(m.Claim)).all()} == {ids["cla"]}
        assert s.get(m.Client, ids["cb"]) is None
        assert s.get(m.Claim, ids["clb"]) is None

    with SessionLocal() as s:
        scoping.bind_principal(s, Principal(user_id="ub", tenant_id=ids["tb"], role=UserRole.admin))
        assert {c.id for c in s.scalars(select(m.Client)).all()} == {ids["cb"]}
        assert s.get(m.Client, ids["ca"]) is None


def test_unscoped_session_is_unfiltered(SessionLocal):
    """System paths (the engine seam, migrations, login) run without a principal and see everything."""
    _seed_two_tenants(SessionLocal)
    with SessionLocal() as s:  # no bind_principal
        assert len(s.scalars(select(m.Client)).all()) == 2
        assert len(s.scalars(select(m.Claim)).all()) == 2


def test_skip_filter_opt_out(SessionLocal):
    ids = _seed_two_tenants(SessionLocal)
    with SessionLocal() as s:
        scoping.bind_principal(s, Principal(user_id="ua", tenant_id=ids["ta"], role=UserRole.admin))
        # explicit opt-out (used by login) bypasses the tenant filter
        all_clients = s.scalars(
            select(m.Client).execution_options(skip_tenant_filter=True)
        ).all()
        assert len(all_clients) == 2
