"""Client routes — list / create / detail (BUILD_PLAN §5, M3).

A client is the importer of record whose drawback the tenant prepares. M3 adds onboarding (create) and
a detail view (programs + a claim/status + accrued-$ rollup) so the cockpit can drill tenant → client
→ program → claim. Tenant isolation is automatic (scoped session); the read-only ``client`` role is
narrowed to its own importer. Creating a client is an admin action (``clients:write``).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.db import models as m
from server.domain import portfolio
from server.domain.enums import UserRole

router = APIRouter(prefix="/api/clients", tags=["clients"])

_ZERO = Decimal("0.00")


def _client_json(c: m.Client) -> dict:
    return {"id": c.id, "name": c.name, "importer_id": c.importer_id, "notes": c.notes}


@router.get("")
def list_clients(
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLIENTS_READ)),
) -> list:
    # Tenant isolation is automatic; a client-role user is further narrowed to its own importer.
    stmt = select(m.Client)
    if principal.role is UserRole.client and principal.client_scope_id:
        stmt = stmt.where(m.Client.id == principal.client_scope_id)
    return [_client_json(c) for c in db.scalars(stmt.order_by(m.Client.name)).all()]


class CreateClientRequest(BaseModel):
    name: str
    importer_id: str
    notes: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(
    req: CreateClientRequest,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLIENTS_WRITE)),
) -> dict:
    client = m.Client(
        tenant_id=principal.tenant_id, name=req.name, importer_id=req.importer_id, notes=req.notes)
    db.add(client)
    db.flush()  # assign client.id before it's referenced by the audit event
    db.add(m.AuditEvent(
        tenant_id=principal.tenant_id, actor_user_id=principal.user_id, action="client.created",
        target_type="client", target_id=client.id,
        detail={"name": req.name, "importer_id": req.importer_id}))
    db.commit()
    return _client_json(client)


@router.get("/{client_id}")
def get_client(
    client_id: str,
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLIENTS_READ)),
) -> dict:
    if principal.role is UserRole.client and client_id != principal.client_scope_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "client not found")
    client = db.get(m.Client, client_id)  # scoped → another tenant's client resolves to None
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "client not found")

    programs = db.scalars(
        select(m.Program).where(m.Program.client_id == client.id).order_by(m.Program.name)).all()
    # Reuse the portfolio accrued rollup, picking out this client's row.
    accrued = next((a for a in portfolio.per_client_accrued(db) if a.client_id == client.id), None)

    out = _client_json(client)
    out["programs"] = [
        {"id": p.id, "name": p.name, "drawback_type": p.drawback_type.value,
         "mfg_ruling_ref": p.mfg_ruling_ref}
        for p in programs
    ]
    out["accrued"] = {
        "claims_total": accrued.claims_total if accrued else 0,
        "pipeline": str(accrued.pipeline if accrued else _ZERO),
        "in_flight": str(accrued.in_flight if accrued else _ZERO),
        "realized": str(accrued.realized if accrued else _ZERO),
    }
    return out
