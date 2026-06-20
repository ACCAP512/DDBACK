#!/usr/bin/env python3
"""Seed a demo broker book-of-business into the dev DB for the M3 cockpit (`make seed`).

    python scripts/seed_broker.py            # resets + seeds ./drawback_dev.db

Builds one broker tenant (Northstar Customs Brokerage) with a user per role, three importer clients,
their programs, and claims spread across every work-queue lane — one of them the **real** demo claim
persisted through the engine seam (so its glass-box designations + traces are explorable). It also
plants undesignated import lines whose 5-year clocks are running, so the expiring-value rollup lights
up. Everything is synthetic; nothing is transmitted to CBP.

The dev DB is reset (drop + create) for a deterministic demo. It is gitignored and dev-only; prod uses
Alembic against Postgres (`DRAWBACK_DATABASE_URL`).
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root → import server
import server  # noqa: E402  -- path bootstrap: also makes `drawback` importable

from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from drawback.config import tariff_eligibility as cfg  # noqa: E402
from drawback.filing.signoff import FilerAttestation, FilerRole, record  # noqa: E402
from drawback.ingest import ingest_dataset  # noqa: E402

from server.auth import service  # noqa: E402
from server.config import SAMPLES_DIR  # noqa: E402
from server.db import models as m  # noqa: E402
from server.db.base import Base, engine  # noqa: E402
from server.domain.enums import ClaimMode, ClaimStatus, DrawbackType, TenantKind, UserRole  # noqa: E402
from server.domain.status import transition_claim  # noqa: E402
from server.services.engine_seam import persist_estimate, run_estimate  # noqa: E402

PASSWORD = "drawback"  # demo-only shared password
SIGNOFF = {
    "filer_name": "Dana Northstar, LCB", "role": FilerRole.LICENSED_CUSTOMS_BROKER,
    "license_number": "CHB-NS-0042",
}

# A lawful path from draft to each target status (BUILD_PLAN status ledger).
_PATH = {
    ClaimStatus.draft: [],
    ClaimStatus.ready: [ClaimStatus.ready],
    ClaimStatus.filed: [ClaimStatus.ready, ClaimStatus.filed],
    ClaimStatus.under_review: [ClaimStatus.ready, ClaimStatus.filed, ClaimStatus.under_review],
    ClaimStatus.liquidated: [ClaimStatus.ready, ClaimStatus.filed, ClaimStatus.liquidated],
    ClaimStatus.paid: [ClaimStatus.ready, ClaimStatus.filed, ClaimStatus.liquidated, ClaimStatus.paid],
}


def _signoff_dict(signer_id: str) -> dict:
    so = record(FilerAttestation(
        filer_name=SIGNOFF["filer_name"], role=SIGNOFF["role"],
        attested_on=datetime.now(timezone.utc).isoformat(), license_number=SIGNOFF["license_number"],
        accepted_defensible=True, accepted_review_understood=True))
    so["signed_by_user_id"] = signer_id
    return so


def _advance(s: Session, claim: m.Claim, target: ClaimStatus, *, signer_id: str,
             actual: Decimal | None = None, claim_number: str | None = None) -> None:
    """Walk ``claim`` from draft to ``target``, signing before it is filed (the compliance gate)."""
    for step in _PATH[target]:
        if step is ClaimStatus.filed and claim.signoff is None:
            claim.signoff = _signoff_dict(signer_id)
        kw = {}
        if step is ClaimStatus.filed and claim_number:
            kw["claim_number"] = claim_number
        if step in (ClaimStatus.liquidated, ClaimStatus.paid) and actual is not None:
            kw["actual_refund"] = actual
        transition_claim(s, claim, step, actor_user_id=signer_id, **kw)


def _synthetic_claim(s: Session, program: m.Program, *, status, estimated, defensible,
                     signer_id, actual=None, period=None) -> m.Claim:
    claim = m.Claim(
        tenant_id=program.tenant_id, program_id=program.id, status=ClaimStatus.draft,
        mode=ClaimMode.retroactive, period=period,
        estimated_refund=Decimal(estimated), defensible_refund=Decimal(defensible),
        tariff_config_version=cfg.VERSION, as_of=cfg.AS_OF)
    s.add(claim)
    s.flush()
    if status is not ClaimStatus.draft:
        _advance(s, claim, status, signer_id=signer_id,
                 actual=None if actual is None else Decimal(actual),
                 claim_number=f"NS-{claim.id[:8].upper()}")
    return claim


def _import_lines(s: Session, client: m.Client, specs) -> None:
    """Plant undesignated import lines (entry, line, qty, base_duty, s301, import_date) → 5-yr clock."""
    for entry, line_no, qty, base_duty, s301, imp in specs:
        s.add(m.ImportEntryLine(
            tenant_id=client.tenant_id, client_id=client.id, entry_number=entry, line_no=line_no,
            hts10="6402999000", import_date=imp, quantity=qty, uom="PRS",
            entered_value=Decimal(qty) * Decimal("18.50"),
            charges={"base_duty": str(base_duty), "section_301": str(s301)}))


def main() -> None:
    print("Resetting dev DB (drop + create) …")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Smk = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    s = Smk()

    tenant = m.Tenant(name="Northstar Customs Brokerage", kind=TenantKind.broker_firm)
    s.add(tenant)
    s.flush()

    # Clients.
    aurora = m.Client(tenant_id=tenant.id, name="Aurora Footwear Imports", importer_id="84-1234567",
                      notes="Footwear; high Section-301 exposure.")
    borealis = m.Client(tenant_id=tenant.id, name="Borealis Auto Parts", importer_id="91-7654321",
                        notes="Tier-1 auto parts; substitution program.")
    cascade = m.Client(tenant_id=tenant.id, name="Cascade Outdoor Gear", importer_id="47-2468013",
                       notes="Newly onboarded — no claims yet.")
    s.add_all([aurora, borealis, cascade])
    s.flush()

    # Programs.
    aurora_prog = m.Program(tenant_id=tenant.id, client_id=aurora.id,
                            name="Footwear Substitution — 1313(j)(2)", drawback_type=DrawbackType.j2)
    borealis_prog = m.Program(tenant_id=tenant.id, client_id=borealis.id,
                              name="Auto Parts Substitution — 1313(j)(2)", drawback_type=DrawbackType.j2)
    cascade_prog = m.Program(tenant_id=tenant.id, client_id=cascade.id,
                             name="Unused Direct-ID — 1313(j)(1)", drawback_type=DrawbackType.j1)
    s.add_all([aurora_prog, borealis_prog, cascade_prog])
    s.flush()

    # Users (one per role; client user scoped to Aurora).
    admin = service.create_user(s, tenant_id=tenant.id, email="admin@northstar.test",
                                password=PASSWORD, name="Avery Admin", role=UserRole.admin)
    service.create_user(s, tenant_id=tenant.id, email="prep@northstar.test", password=PASSWORD,
                        name="Pat Preparer", role=UserRole.preparer)
    service.create_user(s, tenant_id=tenant.id, email="review@northstar.test", password=PASSWORD,
                        name="Robin Reviewer", role=UserRole.reviewer)
    signer = service.create_user(s, tenant_id=tenant.id, email="signer@northstar.test",
                                 password=PASSWORD, name="Sam Signer, LCB", role=UserRole.signer)
    service.create_user(s, tenant_id=tenant.id, email="client@northstar.test", password=PASSWORD,
                        name="Casey Client", role=UserRole.client, client_scope_id=aurora.id)
    s.flush()

    # ── Aurora: the REAL demo claim through the engine seam (rich glass-box). ──
    ds = ingest_dataset(SAMPLES_DIR / "demo_netsuite", SAMPLES_DIR / "demo_customs")
    run = run_estimate(ds)
    real_claim = persist_estimate(s, program=aurora_prog, dataset=ds, run=run,
                                  period="2025-Q4", mode=ClaimMode.retroactive)
    # Leave it in draft so its designations / ledger / audit are explorable from the cockpit.

    # A second Aurora claim, paid (realized $ in the door).
    _synthetic_claim(s, aurora_prog, status=ClaimStatus.paid, estimated="96000.00",
                     defensible="71500.00", actual="70250.00", signer_id=signer.id, period="2025-Q1")

    # ── Borealis: spread across the work-queue lanes. ──
    _synthetic_claim(s, borealis_prog, status=ClaimStatus.ready, estimated="240000.00",
                     defensible="198000.00", signer_id=signer.id, period="2026-Q1")  # awaiting_signoff (gap → exception)
    rtf = _synthetic_claim(s, borealis_prog, status=ClaimStatus.ready, estimated="155000.00",
                           defensible="155000.00", signer_id=signer.id, period="2026-Q1")
    rtf.signoff = _signoff_dict(signer.id)  # signed but not yet filed → ready_to_file
    _synthetic_claim(s, borealis_prog, status=ClaimStatus.filed, estimated="132000.00",
                     defensible="121000.00", signer_id=signer.id, period="2025-Q3")  # filed
    _synthetic_claim(s, borealis_prog, status=ClaimStatus.under_review, estimated="88000.00",
                     defensible="80000.00", signer_id=signer.id, period="2025-Q3")  # cbp_rfi
    _synthetic_claim(s, borealis_prog, status=ClaimStatus.liquidated, estimated="64000.00",
                     defensible="59000.00", actual="58200.00", signer_id=signer.id,
                     period="2025-Q2")  # liquidated

    # Undesignated Borealis import lines with 5-year clocks across the urgency buckets.
    _import_lines(s, borealis, [
        ("BOR-2021-0418", 1, 12000, "21000.00", "54000.00", date(2021, 7, 5)),    # ≤90d
        ("BOR-2021-0419", 2, 8000, "14000.00", "36000.00", date(2021, 9, 1)),     # ≤90d
        ("BOR-2021-1107", 1, 9500, "16500.00", "42500.00", date(2021, 11, 20)),   # ≤180d
        ("BOR-2022-0302", 1, 15000, "26000.00", "67000.00", date(2022, 3, 2)),    # ≤365d
        ("BOR-2023-0815", 1, 11000, "19000.00", "49000.00", date(2023, 8, 15)),   # >1yr
        ("BOR-2024-0101", 1, 20000, "35000.00", "90000.00", date(2024, 1, 1)),    # >1yr
    ])

    s.commit()

    # ── Summary ──
    from server.db import scoping  # noqa: F401
    from server.domain import clock, portfolio
    from server.auth.context import Principal
    sc = Smk()
    scoping.bind_principal(sc, Principal(user_id=admin.id, tenant_id=tenant.id, role=UserRole.admin,
                                         client_scope_id=None))
    roll = clock.expiring_value(sc, as_of=cfg.AS_OF)
    by_status = portfolio.claims_by_status(sc)
    print("\nSeeded Northstar Customs Brokerage:")
    print(f"  clients: 3   programs: 3   users: 5 (login password: '{PASSWORD}')")
    print(f"  claims by status: {by_status}")
    print(f"  real demo claim: est ${run.estimate.headline_point:,.2f} / "
          f"defensible ${run.defensibility.defensible_headline:,.2f} ({len(run.estimate.matched_pairs)} pairs)")
    print(f"  5-year clock: {roll.total_lines} undesignated lines, "
          f"${roll.total_at_risk_duty:,.2f} of eligible duty at risk")
    print("  sign in at /  →  admin@northstar.test / signer@northstar.test / client@northstar.test")
    sc.close()
    s.close()


if __name__ == "__main__":
    main()
