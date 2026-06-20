"""The claim status ledger (BUILD_PLAN §5, M1).

A claim moves through a controlled lifecycle:

    draft → ready → filed → under_review → liquidated → paid

with a couple of lawful step-backs (ready→draft while still editing; under_review→filed when a CBP
request-for-information is resolved). :func:`transition_claim` is the ONLY sanctioned way to change a
claim's status: it rejects illegal transitions, stamps the right timestamp, records the true-up money
figure when CBP liquidates/pays, and writes an :class:`AuditEvent` — so every state change is both
validated and audited.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, FrozenSet, Optional

from sqlalchemy.orm import Session

from server.db.models import AuditEvent, Claim
from server.domain.enums import ClaimStatus

# The lawful transition graph. Forward through the lifecycle, with two explicit step-backs.
ALLOWED_TRANSITIONS: Dict[ClaimStatus, FrozenSet[ClaimStatus]] = {
    ClaimStatus.draft: frozenset({ClaimStatus.ready}),
    ClaimStatus.ready: frozenset({ClaimStatus.filed, ClaimStatus.draft}),
    ClaimStatus.filed: frozenset({ClaimStatus.under_review, ClaimStatus.liquidated}),
    ClaimStatus.under_review: frozenset({ClaimStatus.liquidated, ClaimStatus.filed}),
    ClaimStatus.liquidated: frozenset({ClaimStatus.paid}),
    ClaimStatus.paid: frozenset(),
}


class InvalidTransitionError(Exception):
    """Raised when a claim status change is not permitted by :data:`ALLOWED_TRANSITIONS`."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def can_transition(frm: ClaimStatus, to: ClaimStatus) -> bool:
    return to in ALLOWED_TRANSITIONS.get(frm, frozenset())


def _tenant_id_of(claim: Claim) -> str:
    return claim.program.client.tenant_id


def transition_claim(
    session: Session,
    claim: Claim,
    to: ClaimStatus,
    *,
    actor_user_id: Optional[str] = None,
    claim_number: Optional[str] = None,
    actual_refund: Optional[Decimal] = None,
    at: Optional[datetime] = None,
) -> Claim:
    """Move ``claim`` to status ``to``, validating the transition and auditing it.

    Side effects by destination status:
      * ``filed``      → set ``filed_at`` (and ``claim_number`` if given)
      * ``liquidated`` → set ``liquidated_at`` (and ``actual_refund`` if given — the AP true-up)
      * ``paid``       → set ``paid_at`` (and ``actual_refund`` if given)

    Raises :class:`InvalidTransitionError` on an illegal transition (nothing is changed).
    """
    frm = claim.status
    if not can_transition(frm, to):
        allowed = sorted(s.value for s in ALLOWED_TRANSITIONS.get(frm, frozenset()))
        raise InvalidTransitionError(
            f"claim {claim.id}: {frm.value} → {to.value} is not permitted "
            f"(allowed from {frm.value}: {allowed or 'none'})"
        )

    when = at or _now()
    claim.status = to

    detail: Dict[str, object] = {"from": frm.value, "to": to.value}
    if to is ClaimStatus.filed:
        claim.filed_at = when
        if claim_number is not None:
            claim.claim_number = claim_number
            detail["claim_number"] = claim_number
    elif to is ClaimStatus.liquidated:
        claim.liquidated_at = when
        if actual_refund is not None:
            claim.actual_refund = actual_refund
            detail["actual_refund"] = str(actual_refund)
    elif to is ClaimStatus.paid:
        claim.paid_at = when
        if actual_refund is not None:
            claim.actual_refund = actual_refund
            detail["actual_refund"] = str(actual_refund)

    session.add(
        AuditEvent(
            tenant_id=_tenant_id_of(claim),
            actor_user_id=actor_user_id,
            action=f"claim.status:{frm.value}->{to.value}",
            target_type="claim",
            target_id=claim.id,
            at=when,
            detail=detail,
        )
    )
    session.flush()
    return claim
