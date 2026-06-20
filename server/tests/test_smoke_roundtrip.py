"""M0 gate: round-trip an engine estimate into a persisted Claim with Designations.

Exercises the real pipeline end-to-end — ``ingest_dataset`` (NetSuite × 7501/ACE × AES/EEI) →
``build_estimate`` → ``harden`` → persist — and asserts the engine's numbers survive into the DB
exactly (Decimal-exact) and reconcile.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from drawback.ingest import ingest_dataset

from server.config import SAMPLES_DIR
from server.db import models as m
from server.domain.enums import ClaimMode, ClaimStatus, DrawbackType, TenantKind
from server.services.engine_seam import persist_estimate, run_estimate


def _demo_dataset():
    return ingest_dataset(SAMPLES_DIR / "demo_netsuite", SAMPLES_DIR / "demo_customs")


def _seed_org(session: Session, importer_id: str):
    tenant = m.Tenant(name="Acme Customs Brokerage", kind=TenantKind.broker_firm)
    session.add(tenant)
    session.flush()
    client = m.Client(tenant_id=tenant.id, name="Importer LLC", importer_id=importer_id or "00-0000000")
    program = m.Program(
        tenant_id=tenant.id, client=client, name="Unused substitution (j2)", drawback_type=DrawbackType.j2
    )
    session.add_all([client, program])
    session.flush()
    return program


def test_estimate_roundtrips_into_claim_with_designations(session: Session):
    ds = _demo_dataset()
    run = run_estimate(ds)
    assert run.estimate.matched_pairs, "demo dataset should yield matched pairs (meaningful persistence)"

    program = _seed_org(session, ds.importer_id)
    claim = persist_estimate(
        session, program=program, dataset=ds, run=run, period="2024", mode=ClaimMode.retroactive
    )
    session.commit()

    # The claim carries the engine's headline + defensible figures, exactly.
    assert claim.status is ClaimStatus.draft
    assert claim.estimated_refund == run.estimate.headline_point
    assert claim.defensible_refund == run.defensibility.defensible_headline
    assert claim.tariff_config_version == run.estimate.tariff_config_version

    # One designation per matched pair; the import/export lines are all persisted.
    assert len(claim.designations) == len(run.estimate.matched_pairs)
    assert len(session.scalars(select(m.ImportEntryLine)).all()) == len(ds.imports)
    assert len(session.scalars(select(m.ExportLine)).all()) == len(ds.exports)

    # Headline reconciles: Σ in-headline designation recovery == the claim's estimated refund.
    headline_sum = sum((d.recovery for d in claim.designations if d.in_headline), Decimal("0"))
    assert headline_sum == run.estimate.headline_point

    # Money is exact Decimal, never float.
    assert isinstance(claim.estimated_refund, Decimal)
    assert all(isinstance(d.recovery, Decimal) for d in claim.designations)

    # The creation is audited.
    audits = session.scalars(
        select(m.AuditEvent).where(m.AuditEvent.target_id == claim.id)
    ).all()
    assert [a.action for a in audits] == ["claim.created"]


def test_persisted_claim_reloads_from_a_fresh_session(engine):
    """Prove the data is in the database, not just the identity map — reload in a new Session."""
    ds = _demo_dataset()
    run = run_estimate(ds)

    with Session(engine, expire_on_commit=False) as s:
        program = _seed_org(s, ds.importer_id)
        claim = persist_estimate(s, program=program, dataset=ds, run=run)
        claim_id = claim.id
        s.commit()

    with Session(engine) as s2:
        fresh = s2.get(m.Claim, claim_id)
        assert fresh is not None
        assert fresh.estimated_refund == run.estimate.headline_point
        assert len(fresh.designations) == len(run.estimate.matched_pairs)
        d0 = fresh.designations[0]
        assert d0.import_line is not None and d0.export_line is not None  # linkage survived
        assert d0.trace is not None  # the glass-box basis was persisted
