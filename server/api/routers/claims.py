"""Claim routes — a tenant-scoped read and the **Signer-only** sign-off gate.

Sign-off reuses the engine's licensed-filer attestation (``drawback.filing.signoff``): the app's RBAC
``claims:sign`` permission decides *who in the app* may sign, and the attestation records the *legal
capacity* (licensed broker / attorney / self-filer) — name, role, license, acceptance. Cross-tenant
access is impossible: the scoped session returns ``None`` for another tenant's claim.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from drawback.filing.signoff import FilerAttestation, FilerRole, SignoffError, record

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.db import models as m

router = APIRouter(prefix="/api/claims", tags=["claims"])


def _load_claim(db: Session, claim_id: str) -> m.Claim:
    claim = db.get(m.Claim, claim_id)  # scoped session → another tenant's claim resolves to None
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "claim not found")
    return claim


@router.get("/{claim_id}")
def get_claim(
    claim_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLAIMS_READ)),
) -> dict:
    claim = _load_claim(db, claim_id)
    return {
        "id": claim.id,
        "status": claim.status.value,
        "estimated_refund": None if claim.estimated_refund is None else str(claim.estimated_refund),
        "defensible_refund": None if claim.defensible_refund is None else str(claim.defensible_refund),
        "signoff": claim.signoff,
    }


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
