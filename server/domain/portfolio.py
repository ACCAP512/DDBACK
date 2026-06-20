"""Portfolio rollups for the work-queue home (BUILD_PLAN §5, M3).

This is what flips the tool from a single-claim *calculator* into a *daily* book-of-business cockpit:

* :func:`claims_by_status` — the lifecycle histogram (draft → … → paid).
* :func:`lanes` — the **work-queue lanes** a broker triages each morning: what needs the licensed
  signer, what's ready to transmit, what CBP is asking about, and an **exceptions** lane for claims
  leaving defensible value on the table.
* :func:`per_client_accrued` — money rolled up per client across the lifecycle: *pipeline* (being
  prepared) → *in-flight* (filed, not yet paid) → *realized* (paid).

Everything runs on the request's scoped session, so tenant isolation is automatic
(``server.db.scoping``). Claims are aggregated in Python: a book has far fewer claims than import
lines (each claim spans many lines), so the per-claim pass is cheap — unlike the 5-year clock
(:mod:`server.domain.clock`), which streams the line-level table.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.db.models import Claim, Client, Program
from server.domain.enums import ClaimStatus

_ZERO = Decimal("0.00")


def _money(value: Optional[Decimal]) -> Decimal:
    return _ZERO if value is None else value


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight per-claim card (the unit the cockpit lists render)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ClaimCard:
    id: str
    client_id: str
    client_name: str
    program_id: str
    program_name: str
    drawback_type: str
    status: str
    mode: str
    period: Optional[str]
    estimated: Optional[Decimal]
    defensible: Optional[Decimal]
    actual: Optional[Decimal]
    signed: bool
    filed_at: Optional[datetime]
    liquidated_at: Optional[datetime]
    updated: Optional[datetime]

    @property
    def gap(self) -> Decimal:
        """Estimated minus defensible — value the engine flagged as not (yet) structurally defensible.

        Always ≥ 0: the defensible headline is the VERIFIED-only subset of the estimate. A positive gap
        on a non-final claim is recoverable money worth chasing (missing proof / needs-review)."""
        if self.estimated is None or self.defensible is None:
            return _ZERO
        return self.estimated - self.defensible


def claim_cards(session: Session) -> List[ClaimCard]:
    """Every claim in the tenant as a :class:`ClaimCard`, joined to its program + client names."""
    rows = session.execute(
        select(
            Claim, Program.name, Program.drawback_type, Client.id, Client.name
        )
        .join(Program, Program.id == Claim.program_id)
        .join(Client, Client.id == Program.client_id)
    ).all()
    cards: List[ClaimCard] = []
    for claim, program_name, drawback_type, client_id, client_name in rows:
        cards.append(
            ClaimCard(
                id=claim.id,
                client_id=client_id,
                client_name=client_name,
                program_id=claim.program_id,
                program_name=program_name,
                drawback_type=drawback_type.value,
                status=claim.status.value,
                mode=claim.mode.value,
                period=claim.period,
                estimated=claim.estimated_refund,
                defensible=claim.defensible_refund,
                actual=claim.actual_refund,
                signed=claim.signoff is not None,
                filed_at=claim.filed_at,
                liquidated_at=claim.liquidated_at,
                updated=claim.updated,
            )
        )
    return cards


# ─────────────────────────────────────────────────────────────────────────────
# Claims by status
# ─────────────────────────────────────────────────────────────────────────────
def claims_by_status(session: Session) -> Dict[str, int]:
    """Count of claims in each lifecycle status (every status present as a key, zero-filled)."""
    counts = {s.value: 0 for s in ClaimStatus}
    for status, n in session.execute(
        select(Claim.status, func.count()).group_by(Claim.status)
    ).all():
        counts[status.value] = int(n)
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Work-queue lanes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Lane:
    key: str
    label: str
    hint: str
    count: int
    total_defensible: Decimal
    preview: List[ClaimCard]


def _lane_key(card: ClaimCard) -> Optional[str]:
    """The work lane a claim sits in by status (``ready`` splits on whether it's been signed).

    ``paid`` claims are done — not a work lane (they show in the status histogram + realized $)."""
    if card.status == ClaimStatus.ready.value:
        return "ready_to_file" if card.signed else "awaiting_signoff"
    if card.status == ClaimStatus.draft.value:
        return "draft"
    if card.status == ClaimStatus.filed.value:
        return "filed"
    if card.status == ClaimStatus.under_review.value:
        return "cbp_rfi"
    if card.status == ClaimStatus.liquidated.value:
        return "liquidated"
    return None  # paid


# (key, label, hint) for the status lanes, ordered by daily triage priority.
_LANE_DEFS: List[tuple] = [
    ("awaiting_signoff", "Awaiting sign-off", "Ready claims that need the licensed signer"),
    ("ready_to_file", "Ready to file", "Signed — ready to transmit to CBP"),
    ("cbp_rfi", "CBP review / RFI", "Filed claims CBP is questioning — respond"),
    ("draft", "In preparation", "Drafts still being built"),
    ("filed", "Filed — awaiting liquidation", "Transmitted; waiting on CBP"),
    ("liquidated", "Liquidated — awaiting payment", "Liquidated; refund pending"),
]


def lanes(session: Session, *, preview: int = 5) -> List[Lane]:
    """The triage lanes for the work-queue home: status lanes (priority-ordered) + an exceptions lane.

    Each lane carries its count, the Σ defensible value it holds, and a top-``preview`` card list
    (defensible-descending; exceptions by gap-descending). The exceptions lane is **cross-cutting** —
    a non-final claim with a positive estimated→defensible gap (value flagged not-yet-defensible) — so
    a claim can appear both in its status lane and in exceptions.
    """
    cards = claim_cards(session)
    by_lane: Dict[str, List[ClaimCard]] = {key: [] for key, _, _ in _LANE_DEFS}
    for card in cards:
        key = _lane_key(card)
        if key is not None:
            by_lane[key].append(card)

    out: List[Lane] = []
    for key, label, hint in _LANE_DEFS:
        members = sorted(by_lane[key], key=lambda c: _money(c.defensible), reverse=True)
        out.append(
            Lane(
                key=key,
                label=label,
                hint=hint,
                count=len(members),
                total_defensible=sum((_money(c.defensible) for c in members), _ZERO),
                preview=members[:preview],
            )
        )

    exceptions = sorted(
        (c for c in cards
         if c.status in (ClaimStatus.draft.value, ClaimStatus.ready.value) and c.gap > _ZERO),
        key=lambda c: c.gap,
        reverse=True,
    )
    out.append(
        Lane(
            key="exceptions",
            label="Exceptions — value at review",
            hint="Non-final claims leaving defensible value on the table (chase the proof)",
            count=len(exceptions),
            total_defensible=sum((c.gap for c in exceptions), _ZERO),
            preview=exceptions[:preview],
        )
    )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Per-client accrued $ (pipeline → in-flight → realized)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ClientAccrued:
    client_id: str
    client_name: str
    importer_id: str
    claims_total: int
    pipeline: Decimal      # defensible $ on draft/ready claims (being prepared)
    in_flight: Decimal     # defensible $ on filed/under_review/liquidated claims (submitted, unpaid)
    realized: Decimal      # actual $ on paid claims (money in the door; falls back to defensible)


_PIPELINE = {ClaimStatus.draft.value, ClaimStatus.ready.value}
_IN_FLIGHT = {ClaimStatus.filed.value, ClaimStatus.under_review.value, ClaimStatus.liquidated.value}


def per_client_accrued(session: Session) -> List[ClientAccrued]:
    """Accrued drawback $ per client across the lifecycle. Every client appears (zero-filled), so a
    newly-onboarded client with no claims is still visible on the cockpit."""
    clients = {
        c.id: c for c in session.scalars(select(Client)).all()
    }
    pipeline: Dict[str, Decimal] = {cid: _ZERO for cid in clients}
    in_flight: Dict[str, Decimal] = {cid: _ZERO for cid in clients}
    realized: Dict[str, Decimal] = {cid: _ZERO for cid in clients}
    counts: Dict[str, int] = {cid: 0 for cid in clients}

    for card in claim_cards(session):
        cid = card.client_id
        if cid not in clients:  # defensive — the join guarantees membership
            continue
        counts[cid] += 1
        if card.status in _PIPELINE:
            pipeline[cid] += _money(card.defensible)
        elif card.status in _IN_FLIGHT:
            in_flight[cid] += _money(card.defensible)
        elif card.status == ClaimStatus.paid.value:
            realized[cid] += _money(card.actual if card.actual is not None else card.defensible)

    out = [
        ClientAccrued(
            client_id=cid,
            client_name=c.name,
            importer_id=c.importer_id,
            claims_total=counts[cid],
            pipeline=pipeline[cid],
            in_flight=in_flight[cid],
            realized=realized[cid],
        )
        for cid, c in clients.items()
    ]
    out.sort(key=lambda a: (a.pipeline + a.in_flight + a.realized), reverse=True)
    return out
