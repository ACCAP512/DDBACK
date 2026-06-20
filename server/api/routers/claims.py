"""Claim routes — list, detail (+ glass-box designations / ledger / audit), lifecycle, and the
**Signer-only** sign-off gate (BUILD_PLAN §5, M3; sign-off from M2).

The persisted claim's stored designations + traces are what the frontend's estimate / glass-box /
defensibility / filing tabs render — the engine's once-ephemeral outputs, now durable and navigable.

* ``GET  /api/claims``                  — list (filter by status/client/program; paginated)
* ``GET  /api/claims/{id}``             — detail (money, sign-off, designation summary, next steps)
* ``GET  /api/claims/{id}/designations`` — the glass-box: every matched pair + its trace
* ``GET  /api/claims/{id}/ledger``      — per-import-line available → designated → remaining
* ``GET  /api/claims/{id}/audit``       — the append-only audit trail
* ``POST /api/claims/{id}/transition``  — advance the lifecycle (can't **file** an unsigned claim)
* ``POST /api/claims/{id}/signoff``     — the licensed-filer attestation (Signer only)

Cross-tenant access is impossible: the scoped session returns ``None`` for another tenant's claim.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from drawback.filing.signoff import FilerAttestation, FilerRole, SignoffError, record

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.db import models as m
from server.domain.enums import ClaimStatus, UserRole
from server.domain.ledger import import_line_ledger
from server.domain.status import ALLOWED_TRANSITIONS, InvalidTransitionError, transition_claim

router = APIRouter(prefix="/api/claims", tags=["claims"])

_ZERO = Decimal("0.00")


def _money(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else str(value)


def _dt(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _d(value: Optional[date]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _load_claim(db: Session, claim_id: str) -> m.Claim:
    claim = db.get(m.Claim, claim_id)  # scoped session → another tenant's claim resolves to None
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "claim not found")
    return claim


def _client_guard(principal: Principal, client_id: str) -> None:
    """A client-role user may only touch claims under its own importer."""
    if principal.role is UserRole.client and client_id != principal.client_scope_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "claim not found")


# ── list ──────────────────────────────────────────────────────────────────────
def _card(claim: m.Claim, program: m.Program, client: m.Client) -> dict:
    est, defn = claim.estimated_refund, claim.defensible_refund
    gap = (est - defn) if (est is not None and defn is not None) else None
    return {
        "id": claim.id,
        "client_id": client.id,
        "client_name": client.name,
        "program_id": program.id,
        "program_name": program.name,
        "drawback_type": program.drawback_type.value,
        "status": claim.status.value,
        "mode": claim.mode.value,
        "period": claim.period,
        "estimated": _money(est),
        "defensible": _money(defn),
        "actual": _money(claim.actual_refund),
        "gap": _money(gap),
        "signed": claim.signoff is not None,
        "filed_at": _dt(claim.filed_at),
        "updated": _dt(claim.updated),
    }


@router.get("")
def list_claims(
    status_filter: Optional[str] = Query(None, alias="status", description="filter by claim status"),
    client_id: Optional[str] = Query(None),
    program_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    filters = []
    if status_filter is not None:
        try:
            filters.append(m.Claim.status == ClaimStatus(status_filter))
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"invalid status '{status_filter}' — one of {[s.value for s in ClaimStatus]}")
    if program_id is not None:
        filters.append(m.Claim.program_id == program_id)

    # Client-role users see only their own importer's claims; everyone else may filter by client.
    effective_client = principal.client_scope_id if principal.role is UserRole.client else client_id
    if effective_client is not None:
        filters.append(m.Client.id == effective_client)

    base = (
        select(m.Claim, m.Program, m.Client)
        .join(m.Program, m.Program.id == m.Claim.program_id)
        .join(m.Client, m.Client.id == m.Program.client_id)
        .where(*filters)
    )
    total = db.scalar(
        select(func.count())
        .select_from(m.Claim)
        .join(m.Program, m.Program.id == m.Claim.program_id)
        .join(m.Client, m.Client.id == m.Program.client_id)
        .where(*filters)
    )
    rows = db.execute(
        base.order_by(m.Claim.updated.desc()).limit(limit).offset(offset)
    ).all()
    return {
        "claims": [_card(claim, program, client) for claim, program, client in rows],
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
    }


# ── detail ────────────────────────────────────────────────────────────────────
@router.get("/{claim_id}")
def get_claim(
    claim_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    claim = _load_claim(db, claim_id)
    program = claim.program
    client = program.client
    _client_guard(principal, client.id)

    designations = claim.designations
    recovery_total = sum((d.recovery for d in designations), _ZERO)
    headline = [d for d in designations if d.in_headline]
    headline_total = sum((d.recovery for d in headline), _ZERO)

    return {
        "id": claim.id,
        "status": claim.status.value,
        "mode": claim.mode.value,
        "period": claim.period,
        "client": {"id": client.id, "name": client.name, "importer_id": client.importer_id},
        "program": {
            "id": program.id, "name": program.name,
            "drawback_type": program.drawback_type.value, "mfg_ruling_ref": program.mfg_ruling_ref,
        },
        "estimated_refund": _money(claim.estimated_refund),
        "defensible_refund": _money(claim.defensible_refund),
        "actual_refund": _money(claim.actual_refund),
        "claim_number": claim.claim_number,
        "signoff": claim.signoff,
        "tariff_config_version": claim.tariff_config_version,
        "as_of": _d(claim.as_of),
        "filed_at": _dt(claim.filed_at),
        "liquidated_at": _dt(claim.liquidated_at),
        "paid_at": _dt(claim.paid_at),
        "created": _dt(claim.created),
        "updated": _dt(claim.updated),
        "designation_summary": {
            "count": len(designations),
            "recovery_total": _money(recovery_total),
            "in_headline_count": len(headline),
            "headline_total": _money(headline_total),
        },
        "allowed_transitions": sorted(s.value for s in ALLOWED_TRANSITIONS.get(claim.status, frozenset())),
    }


# ── glass-box: designations + traces ──────────────────────────────────────────
@router.get("/{claim_id}/designations")
def claim_designations(
    claim_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    claim = _load_claim(db, claim_id)
    _client_guard(principal, claim.program.client.id)

    items = []
    for d in claim.designations:
        il, el = d.import_line, d.export_line
        items.append({
            "id": d.id,
            "quantity": d.quantity,
            "provision": d.provision,
            "per_unit_recovery": _money(d.per_unit_recovery),
            "recovery": _money(d.recovery),
            "recovery_low": _money(d.recovery_low),
            "confidence": d.confidence,
            "in_headline": d.in_headline,
            "import_line": {
                "id": il.id, "entry_number": il.entry_number, "line_no": il.line_no,
                "hts10": il.hts10, "import_date": _d(il.import_date),
            },
            "export_line": {
                "id": el.id, "reference": el.reference, "hts10": el.hts10,
                "export_date": _d(el.export_date), "itn": el.itn,
            },
            "trace": d.trace,
        })
    items.sort(key=lambda x: (not x["in_headline"], x["recovery"] or ""), reverse=False)
    return {"claim_id": claim.id, "designations": items, "count": len(items)}


# ── designation ledger for this claim's import lines ──────────────────────────
@router.get("/{claim_id}/ledger")
def claim_ledger(
    claim_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    claim = _load_claim(db, claim_id)
    _client_guard(principal, claim.program.client.id)

    # Distinct import lines this claim designates against (dedup, preserve first-seen order).
    seen, lines = set(), []
    for d in claim.designations:
        if d.import_entry_line_id not in seen:
            seen.add(d.import_entry_line_id)
            lines.append(d.import_line)

    rows = []
    for line in lines:
        led = import_line_ledger(db, line)
        rows.append({
            "import_entry_line_id": led.import_entry_line_id,
            "entry_number": led.entry_number,
            "line_no": led.line_no,
            "available_qty": led.available_qty,
            "designated_qty": led.designated_qty,
            "remaining_qty": led.remaining_qty,
            "per_unit_duty": _money(led.per_unit_duty),
            "available_duty": _money(led.available_duty),
            "designated_duty": _money(led.designated_duty),
            "remaining_duty": _money(led.remaining_duty),
        })
    return {"claim_id": claim.id, "lines": rows}


# ── audit trail ───────────────────────────────────────────────────────────────
@router.get("/{claim_id}/audit")
def claim_audit(
    claim_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    claim = _load_claim(db, claim_id)
    _client_guard(principal, claim.program.client.id)
    events = db.scalars(
        select(m.AuditEvent)
        .where(m.AuditEvent.target_type == "claim", m.AuditEvent.target_id == claim.id)
        .order_by(m.AuditEvent.at.desc())
    ).all()
    return {
        "claim_id": claim.id,
        "events": [
            {"action": e.action, "actor_user_id": e.actor_user_id, "at": _dt(e.at), "detail": e.detail}
            for e in events
        ],
    }


# ── lifecycle transition ──────────────────────────────────────────────────────
class TransitionRequest(BaseModel):
    to: str  # ClaimStatus
    claim_number: Optional[str] = None
    actual_refund: Optional[str] = None  # decimal string (the true-up at liquidation/payment)


@router.post("/{claim_id}/transition")
def transition(
    claim_id: str,
    req: TransitionRequest,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_WRITE)),
) -> dict:
    claim = _load_claim(db, claim_id)
    _client_guard(principal, claim.program.client.id)
    try:
        to_status = ClaimStatus(req.to)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"invalid status '{req.to}' — one of {[s.value for s in ClaimStatus]}")

    # Compliance gate: a claim cannot be FILED until the licensed signer has certified it.
    if to_status is ClaimStatus.filed and claim.signoff is None:
        raise HTTPException(
            status.HTTP_428_PRECONDITION_REQUIRED,
            "claim must be signed off by a licensed filer before it can be filed")

    actual: Optional[Decimal] = None
    if req.actual_refund is not None:
        try:
            actual = Decimal(req.actual_refund)
        except (InvalidOperation, ValueError):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"invalid actual_refund '{req.actual_refund}'")

    try:
        transition_claim(
            db, claim, to_status,
            actor_user_id=principal.user_id, claim_number=req.claim_number, actual_refund=actual)
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    db.commit()
    return {
        "id": claim.id,
        "status": claim.status.value,
        "filed_at": _dt(claim.filed_at),
        "liquidated_at": _dt(claim.liquidated_at),
        "paid_at": _dt(claim.paid_at),
        "actual_refund": _money(claim.actual_refund),
        "claim_number": claim.claim_number,
        "allowed_transitions": sorted(s.value for s in ALLOWED_TRANSITIONS.get(claim.status, frozenset())),
    }


# ── sign-off (Signer only) ────────────────────────────────────────────────────
class SignoffRequest(BaseModel):
    filer_name: str
    role: str  # FilerRole: licensed_customs_broker | customs_attorney | self_filer_own_account
    license_number: str = ""
    accepted_defensible: bool = False
    accepted_review_understood: bool = False


@router.post("/{claim_id}/signoff")
def signoff_claim(
    claim_id: str,
    req: SignoffRequest,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_SIGN)),
) -> dict:
    claim = _load_claim(db, claim_id)
    _client_guard(principal, claim.program.client.id)
    try:
        filer_role = FilerRole(req.role)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"invalid filer role '{req.role}' — must be one of {[r.value for r in FilerRole]}",
        )
    attestation = FilerAttestation(
        filer_name=req.filer_name,
        role=filer_role,
        attested_on=datetime.now(timezone.utc).isoformat(),
        license_number=req.license_number,
        accepted_defensible=req.accepted_defensible,
        accepted_review_understood=req.accepted_review_understood,
    )
    try:
        signoff = record(attestation)
    except SignoffError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    signoff["signed_by_user_id"] = principal.user_id
    claim.signoff = signoff
    db.add(
        m.AuditEvent(
            tenant_id=claim.tenant_id,
            actor_user_id=principal.user_id,
            action="claim.signoff",
            target_type="claim",
            target_id=claim.id,
            detail={"filer_name": signoff["filer_name"], "role": signoff["role"]},
        )
    )
    db.commit()
    return {"claim_id": claim.id, "signoff": signoff}
