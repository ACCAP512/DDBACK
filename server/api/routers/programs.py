"""Program routes — list / create / detail (BUILD_PLAN §5, M3).

A program is a drawback provision + its configuration for one client; it groups the client's claims.
M3 covers the navigation + onboarding surface (list under a client, create, detail with a claim
rollup). The CBP-vocabulary config (privileges AP/WPN/OTW, accounting method, eligible layers) is
fleshed out in M6 — here ``config`` is an opaque JSON bag accepted as-is.

Tenant isolation is automatic (scoped session). Writes carry ``programs:write`` (preparer + admin);
the read-only ``client`` role is narrowed to its own importer.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.db import models as m
from server.domain.enums import ClaimStatus, DrawbackType, UserRole

router = APIRouter(prefix="/api/programs", tags=["programs"])


def _program_json(p: m.Program) -> dict:
    return {
        "id": p.id,
        "client_id": p.client_id,
        "name": p.name,
        "drawback_type": p.drawback_type.value,
        "config": p.config,
        "mfg_ruling_ref": p.mfg_ruling_ref,
    }


def _client_visible(principal: Principal, client_id: Optional[str]) -> Optional[str]:
    """For the client role, force the client filter to its own scope (else honor the given filter)."""
    if principal.role is UserRole.client:
        return principal.client_scope_id
    return client_id


@router.get("")
def list_programs(
    client_id: Optional[str] = Query(None, description="filter to one client"),
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.PROGRAMS_READ)),
) -> list:
    stmt = select(m.Program)
    scoped_client = _client_visible(principal, client_id)
    if scoped_client:
        stmt = stmt.where(m.Program.client_id == scoped_client)
    stmt = stmt.order_by(m.Program.name)
    return [_program_json(p) for p in db.scalars(stmt).all()]


class CreateProgramRequest(BaseModel):
    client_id: str
    name: str
    drawback_type: str  # DrawbackType: j1 | j2 | a | b | c
    config: dict = Field(default_factory=dict)
    mfg_ruling_ref: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_program(
    req: CreateProgramRequest,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.PROGRAMS_WRITE)),
) -> dict:
    try:
        dtype = DrawbackType(req.drawback_type)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"invalid drawback_type '{req.drawback_type}' — one of {[d.value for d in DrawbackType]}")
    # The client must exist in this tenant (scoped get → another tenant's client is invisible → 404).
    client = db.get(m.Client, req.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "client not found")

    program = m.Program(
        tenant_id=principal.tenant_id, client_id=client.id, name=req.name,
        drawback_type=dtype, config=req.config, mfg_ruling_ref=req.mfg_ruling_ref)
    db.add(program)
    db.flush()  # assign program.id before it's referenced by the audit event
    db.add(m.AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id, action="program.created",
        target_type="program", target_id=program.id,
        detail={"client_id": client.id, "name": req.name, "drawback_type": dtype.value}))
    db.commit()
    return _program_json(program)


@router.get("/{program_id}")
def get_program(
    program_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.PROGRAMS_READ)),
) -> dict:
    program = db.get(m.Program, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "program not found")
    if principal.role is UserRole.client and program.client_id != principal.client_scope_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "program not found")

    by_status = {s.value: 0 for s in ClaimStatus}
    for st, n in db.execute(
        select(m.Claim.status, func.count())
        .where(m.Claim.program_id == program.id)
        .group_by(m.Claim.status)
    ).all():
        by_status[st.value] = int(n)

    out = _program_json(program)
    out["claims_by_status"] = by_status
    out["claims_total"] = sum(by_status.values())
    return out
