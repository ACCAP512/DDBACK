"""M1 — the claim status ledger: validated lifecycle transitions, money/timestamp updates, audit."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.db import models as m
from server.domain.enums import ClaimStatus, DrawbackType, TenantKind
from server.domain.status import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    can_transition,
    transition_claim,
)


def _seed_claim(session: Session, status: ClaimStatus = ClaimStatus.draft) -> m.Claim:
    tenant = m.Tenant(name="Acme", kind=TenantKind.broker_firm)
    session.add(tenant)
    session.flush()
    client = m.Client(tenant_id=tenant.id, name="Importer LLC", importer_id="12-3456789")
    program = m.Program(tenant_id=tenant.id, client=client, name="J2", drawback_type=DrawbackType.j2)
    claim = m.Claim(tenant_id=tenant.id, program=program, status=status)
    session.add_all([client, program, claim])
    session.flush()
    return claim


def _audit_count(session: Session, claim: m.Claim) -> int:
    return session.scalar(
        select(func.count()).select_from(m.AuditEvent).where(m.AuditEvent.target_id == claim.id)
    )


def test_full_lifecycle_sets_timestamps_money_and_audits_each_step(session: Session):
    claim = _seed_claim(session)
    at = datetime(2026, 3, 1, tzinfo=timezone.utc)

    transition_claim(session, claim, ClaimStatus.ready)
    transition_claim(session, claim, ClaimStatus.filed, claim_number="2024-DRW-001", at=at)
    assert claim.status is ClaimStatus.filed
    assert claim.claim_number == "2024-DRW-001"
    assert claim.filed_at == at

    transition_claim(session, claim, ClaimStatus.liquidated, actual_refund=Decimal("11875.48"), at=at)
    assert claim.liquidated_at == at
    assert claim.actual_refund == Decimal("11875.48")

    transition_claim(session, claim, ClaimStatus.paid, at=at)
    assert claim.status is ClaimStatus.paid
    assert claim.paid_at == at

    # Every one of the four transitions is audited.
    audits = session.scalars(
        select(m.AuditEvent).where(m.AuditEvent.target_id == claim.id)
    ).all()
    assert len(audits) == 4
    assert all(a.action.startswith("claim.status:") for a in audits)
    assert any(a.detail.get("to") == "paid" for a in audits)


def test_illegal_transition_raises_and_changes_nothing(session: Session):
    claim = _seed_claim(session, status=ClaimStatus.draft)
    with pytest.raises(InvalidTransitionError):
        transition_claim(session, claim, ClaimStatus.paid)  # draft → paid is not permitted
    assert claim.status is ClaimStatus.draft
    assert claim.filed_at is None
    assert _audit_count(session, claim) == 0  # nothing audited on a rejected transition


def test_step_back_allowed_but_skips_are_not(session: Session):
    claim = _seed_claim(session, status=ClaimStatus.ready)
    transition_claim(session, claim, ClaimStatus.draft)  # lawful step-back
    assert claim.status is ClaimStatus.draft
    with pytest.raises(InvalidTransitionError):
        transition_claim(session, claim, ClaimStatus.filed)  # draft → filed skips 'ready'


def test_transition_map_total_and_terminal():
    for status in ClaimStatus:
        assert status in ALLOWED_TRANSITIONS, f"{status} missing from the transition map"
    assert ALLOWED_TRANSITIONS[ClaimStatus.paid] == frozenset()  # paid is terminal
    assert can_transition(ClaimStatus.draft, ClaimStatus.ready)
    assert not can_transition(ClaimStatus.draft, ClaimStatus.filed)
