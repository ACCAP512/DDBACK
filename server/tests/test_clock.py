"""M3 — the 5-year expiring-value clock (BUILD_PLAN §5).

Engine-grade rigor: a wrong deadline or an overstated at-risk figure misleads the broker about
real money, so this pins the statutory window (reused from the engine), the eligible-duty filter
(reused from the dated config), the undesignated-proration, the urgency buckets, and tenant isolation.

Pattern: seed on an **unscoped** session (so a test can plant two tenants' rows), commit, then read
through a session **scoped** to one tenant — exactly how a request runs.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from drawback.rules.time_windows import five_year_deadline

from server.auth.context import Principal
from server.db import models as m
from server.db import scoping
from server.db.base import Base, make_engine
from server.domain import clock
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind, UserRole


@pytest.fixture()
def Smk(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'clock.db'}")
    Base.metadata.create_all(eng)
    yield sessionmaker(bind=eng, expire_on_commit=False, class_=Session)
    eng.dispose()


def _scoped(Smk, tenant_id: str) -> Session:
    s = Smk()
    scoping.bind_principal(s, Principal(user_id="u", tenant_id=tenant_id, role=UserRole.admin,
                                        client_scope_id=None))
    return s


def _tenant_client(s: Session, name: str) -> tuple:
    t = m.Tenant(name=name, kind=TenantKind.broker_firm)
    s.add(t); s.flush()
    c = m.Client(tenant_id=t.id, name=f"{name}-imp", importer_id="11-1111111")
    s.add(c); s.flush()
    return t, c


def _import_line(s, client, *, entry, line_no, qty, charges, import_date) -> m.ImportEntryLine:
    row = m.ImportEntryLine(
        tenant_id=client.tenant_id, client_id=client.id, entry_number=entry, line_no=line_no,
        hts10="6402999000", import_date=import_date, quantity=qty, uom="EA",
        entered_value=Decimal("1000.00"), charges=charges,
    )
    s.add(row); s.flush()
    return row


def _designate(s, client, import_line, qty) -> None:
    """Persist a designation of ``qty`` units against ``import_line`` (clock cares only about qty)."""
    program = m.Program(tenant_id=client.tenant_id, client_id=client.id, name="p",
                        drawback_type=DrawbackType.j2)
    s.add(program); s.flush()
    claim = m.Claim(tenant_id=client.tenant_id, program_id=program.id, status=ClaimStatus.draft)
    s.add(claim); s.flush()
    export = m.ExportLine(tenant_id=client.tenant_id, client_id=client.id,
                         reference=f"BOL-{import_line.entry_number}-{import_line.line_no}",
                         hts10="6402999000", export_date=date(2023, 1, 1), quantity=qty, uom="EA",
                         value_per_unit=Decimal("20.00"))
    s.add(export); s.flush()
    s.add(m.Designation(
        tenant_id=client.tenant_id, claim_id=claim.id, import_entry_line_id=import_line.id,
        export_line_id=export.id, quantity=qty, provision="59",
        per_unit_designated_duty=Decimal("0.50"), per_unit_recovery=Decimal("0.49"),
        recovery=Decimal("0.49") * qty, recovery_low=Decimal("0.49") * qty, confidence="VERIFIED",
    ))
    s.flush()


# ── eligible-duty filter reuses the dated engine config ───────────────────────
def test_eligible_duty_paid_counts_only_eligible_layers():
    charges = {
        "base_duty": "50.00",      # eligible
        "section_301": "30.00",    # eligible
        "mpf": "10.00",            # eligible
        "hmf": "5.00",             # eligible
        "section_232": "200.00",   # NOT eligible
        "ad_cvd": "300.00",        # NOT eligible
        "ieepa": "400.00",         # NOT eligible (CAPE, not drawback)
        "mystery_layer": "9.99",   # unknown → conservatively excluded
    }
    assert clock.eligible_duty_paid(charges) == Decimal("95.00")  # 50+30+10+5
    assert clock.eligible_duty_paid({}) == Decimal("0")


# ── deadline reuses the engine's statutory math, exactly ──────────────────────
def test_deadline_matches_engine_and_days_remaining(Smk):
    w = Smk()
    _, c = _tenant_client(w, "T")
    line = _import_line(w, c, entry="E1", line_no=1, qty=100,
                        charges={"base_duty": "100.00"}, import_date=date(2022, 3, 15))
    tenant_id = c.tenant_id
    w.commit(); w.close()

    s = _scoped(Smk, tenant_id)
    as_of = date(2026, 6, 20)
    lc = clock.line_clock(s.get(m.ImportEntryLine, line.id), designated_qty=0, as_of=as_of)
    assert lc.deadline == five_year_deadline(date(2022, 3, 15)) == date(2027, 3, 15)
    assert lc.days_remaining == (date(2027, 3, 15) - as_of).days


# ── at-risk prorates to the UNDESIGNATED units; eligible pool is whole-line ────
def test_at_risk_prorates_by_undesignated_fraction(Smk):
    w = Smk()
    _, c = _tenant_client(w, "T")
    line = _import_line(w, c, entry="E1", line_no=1, qty=100,
                        charges={"base_duty": "50.00", "mpf": "10.00", "section_232": "999.00"},
                        import_date=date(2024, 1, 1))
    _designate(w, c, line, 40)  # 40 of 100 designated → 60 remaining
    tenant_id, line_id = c.tenant_id, line.id
    w.commit(); w.close()

    s = _scoped(Smk, tenant_id)
    lc = clock.line_clock(s.get(m.ImportEntryLine, line_id), designated_qty=40, as_of=date(2026, 6, 20))
    assert lc.eligible_duty_paid == Decimal("60.00")          # 50 + 10 (232 excluded)
    assert lc.remaining_qty == 60
    assert lc.at_risk_duty == Decimal("36.00")                # 60 * 60/100

    # And through the full rollup (which derives designated_qty from the ledger itself).
    roll = clock.expiring_value(s, as_of=date(2026, 6, 20))
    assert roll.total_lines == 1
    assert roll.total_at_risk_duty == Decimal("36.00")


def test_fully_designated_line_drops_out_of_the_rollup(Smk):
    w = Smk()
    _, c = _tenant_client(w, "T")
    line = _import_line(w, c, entry="E9", line_no=1, qty=100,
                        charges={"base_duty": "100.00"}, import_date=date(2024, 1, 1))
    _designate(w, c, line, 100)  # fully designated → nothing at risk
    tenant_id = c.tenant_id
    w.commit(); w.close()

    s = _scoped(Smk, tenant_id)
    roll = clock.expiring_value(s, as_of=date(2026, 6, 20))
    assert roll.total_lines == 0
    assert roll.total_at_risk_duty == Decimal("0.00")


# ── urgency buckets ───────────────────────────────────────────────────────────
def test_buckets_partition_lines_by_urgency(Smk):
    w = Smk()
    _, c = _tenant_client(w, "T")
    # import_date → expected bucket (deadline = import_date + 5y, relative to as_of=2026-06-20)
    cases = {
        "expired": date(2021, 1, 1),   # deadline 2026-01-01 (past)
        "lte_90": date(2021, 7, 1),    # deadline 2026-07-01 (~11 days)
        "lte_180": date(2021, 11, 1),  # deadline 2026-11-01 (~134 days)
        "lte_365": date(2022, 3, 1),   # deadline 2027-03-01 (~254 days)
        "gt_365": date(2024, 1, 1),    # deadline 2029-01-01 (far)
    }
    for i, imp in enumerate(cases.values(), start=1):
        _import_line(w, c, entry=f"E{i}", line_no=1, qty=10,
                     charges={"base_duty": "10.00"}, import_date=imp)
    tenant_id = c.tenant_id
    w.commit(); w.close()

    s = _scoped(Smk, tenant_id)
    roll = clock.expiring_value(s, as_of=date(2026, 6, 20))
    got = {b.key: b.lines for b in roll.buckets}
    assert got == {"expired": 1, "lte_90": 1, "lte_180": 1, "lte_365": 1, "gt_365": 1}
    assert roll.total_lines == 5
    # soonest is deadline-ascending → the expired line first, then the ≤90-day one.
    assert [c.bucket for c in roll.soonest][:2] == ["expired", "lte_90"]


# ── tenant isolation ──────────────────────────────────────────────────────────
def test_clock_is_tenant_isolated(Smk):
    w = Smk()
    _, ca = _tenant_client(w, "A")
    _, cb = _tenant_client(w, "B")
    _import_line(w, ca, entry="A1", line_no=1, qty=100, charges={"base_duty": "100.00"},
                 import_date=date(2024, 1, 1))
    _import_line(w, cb, entry="B1", line_no=1, qty=100, charges={"base_duty": "777.00"},
                 import_date=date(2024, 1, 1))
    tenant_a = ca.tenant_id
    w.commit(); w.close()

    sa = _scoped(Smk, tenant_a)
    roll_a = clock.expiring_value(sa, as_of=date(2026, 6, 20))
    assert roll_a.total_lines == 1
    assert roll_a.total_at_risk_duty == Decimal("100.00")  # A only — never sees B's 777
