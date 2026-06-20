"""M1 — the designation ledger: across-time conservation (19 U.S.C. 1313(v)) + the per-line view.

Engine-grade rigor for the make-or-break control: double-designation across claims and over time must
be structurally impossible to persist.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from drawback.ingest import ingest_dataset

from server.config import SAMPLES_DIR
from server.db import models as m
from server.domain import ledger
from server.domain.enums import DrawbackType, TenantKind
from server.services.engine_seam import persist_estimate, run_estimate


# ── seeding helpers ──────────────────────────────────────────────────────────
def _seed_chain(session: Session):
    tenant = m.Tenant(name="Acme Brokerage", kind=TenantKind.broker_firm)
    session.add(tenant)
    session.flush()
    client = m.Client(tenant_id=tenant.id, name="Importer LLC", importer_id="12-3456789")
    program = m.Program(tenant_id=tenant.id, client=client, name="J2", drawback_type=DrawbackType.j2)
    session.add_all([client, program])
    session.flush()
    return client, program


def _claim(session: Session, program: m.Program) -> m.Claim:
    claim = m.Claim(tenant_id=program.tenant_id, program_id=program.id)
    session.add(claim)
    session.flush()
    return claim


def _import_line(session, client, *, entry="E1", line=1, qty=100):
    row = m.ImportEntryLine(
        tenant_id=client.tenant_id, client_id=client.id, entry_number=entry, line_no=line,
        hts10="8501314000", import_date=date(2024, 1, 1), quantity=qty, uom="EA",
        entered_value=Decimal("1000.00"), charges={}, liquidated=True,
    )
    session.add(row)
    session.flush()
    return row


def _export_line(session, client, *, ref="X1", qty=100):
    row = m.ExportLine(
        tenant_id=client.tenant_id, client_id=client.id, reference=ref, hts10="8501314000",
        export_date=date(2024, 6, 1), quantity=qty, uom="EA", value_per_unit=Decimal("50.00"),
    )
    session.add(row)
    session.flush()
    return row


def _designate(session, client, claim, imp, exp, qty, pud=Decimal("2.50")):
    row = m.Designation(
        tenant_id=client.tenant_id, claim=claim, import_line=imp, export_line=exp, quantity=qty,
        provision="59", per_unit_designated_duty=pud, per_unit_recovery=pud,
        recovery=(pud * Decimal("0.99") * Decimal(qty)).quantize(Decimal("0.01")),
        recovery_low=Decimal("0.00"), confidence="high", in_headline=True, trace=None,
    )
    session.add(row)
    session.flush()
    return row


# ── the per-line ledger view ─────────────────────────────────────────────────
def test_import_line_ledger_view_qty_and_duty(session: Session):
    client, program = _seed_chain(session)
    claim = _claim(session, program)
    imp = _import_line(session, client, qty=100)
    exp = _export_line(session, client, qty=100)
    _designate(session, client, claim, imp, exp, qty=60, pud=Decimal("2.50"))

    view = ledger.import_line_ledger(session, imp)
    assert (view.available_qty, view.designated_qty, view.remaining_qty) == (100, 60, 40)
    assert view.per_unit_duty == Decimal("2.50")
    assert view.available_duty == Decimal("250.00")
    assert view.designated_duty == Decimal("150.00")
    assert view.remaining_duty == Decimal("100.00")


def test_ledger_sums_designations_across_multiple_claims(session: Session):
    client, program = _seed_chain(session)
    imp = _import_line(session, client, qty=100)
    exp1 = _export_line(session, client, ref="X1", qty=50)
    exp2 = _export_line(session, client, ref="X2", qty=50)
    _designate(session, client, _claim(session, program), imp, exp1, qty=30)
    _designate(session, client, _claim(session, program), imp, exp2, qty=25)

    view = ledger.import_line_ledger(session, imp)
    assert view.designated_qty == 55  # summed across the two claims
    assert view.remaining_qty == 45


# ── the conservation invariant (raises) ──────────────────────────────────────
def test_overdesignation_across_claims_raises(session: Session):
    client, program = _seed_chain(session)
    imp = _import_line(session, client, entry="E1", line=1, qty=100)
    exp = _export_line(session, client, ref="X1", qty=100)
    _designate(session, client, _claim(session, program), imp, exp, qty=60)
    session.commit()  # 60 already designated, across time

    key = ("E1", 1)
    # 60 + 41 = 101 > 100 → raise
    with pytest.raises(ledger.OverDesignationError) as exc:
        ledger.assert_capacity_available(
            session, client_id=client.id, import_proposed={key: 41},
            import_capacity={key: 100}, export_proposed={}, export_capacity={},
        )
    (v,) = exc.value.violations
    assert v.kind == "import" and v.available == 100 and v.would_total == 101

    # 60 + 40 = 100 exactly → fits, no raise
    ledger.assert_capacity_available(
        session, client_id=client.id, import_proposed={key: 40},
        import_capacity={key: 100}, export_proposed={}, export_capacity={},
    )


def test_export_side_conservation_raises(session: Session):
    client, program = _seed_chain(session)
    imp = _import_line(session, client, qty=1000)
    exp = _export_line(session, client, ref="X1", qty=50)
    _designate(session, client, _claim(session, program), imp, exp, qty=50)
    session.commit()  # the export is fully used

    with pytest.raises(ledger.OverDesignationError):
        ledger.assert_capacity_available(
            session, client_id=client.id, import_proposed={}, import_capacity={},
            export_proposed={"X1": 1}, export_capacity={"X1": 50},
        )


# ── integration: persist_estimate enforces it end-to-end ─────────────────────
def _demo_dataset():
    return ingest_dataset(SAMPLES_DIR / "demo_netsuite", SAMPLES_DIR / "demo_customs")


def test_persist_estimate_blocks_double_claim_on_same_dataset(session: Session):
    ds = _demo_dataset()
    run = run_estimate(ds)
    client, program = _seed_chain(session)

    persist_estimate(session, program=program, dataset=ds, run=run)  # claim 1
    session.commit()
    n_designations = session.scalar(select(func.count()).select_from(m.Designation))
    assert session.scalar(select(func.count()).select_from(m.Claim)) == 1
    assert n_designations == len(run.estimate.matched_pairs)

    # Re-running the SAME dataset designates the same lines again → 1313(v) violation.
    with pytest.raises(ledger.OverDesignationError):
        persist_estimate(session, program=program, dataset=ds, run=run)
    session.rollback()

    # Nothing partial persisted: still one claim, same designation count.
    assert session.scalar(select(func.count()).select_from(m.Claim)) == 1
    assert session.scalar(select(func.count()).select_from(m.Designation)) == n_designations
