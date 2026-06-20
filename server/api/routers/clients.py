"""Client routes — a tenant-scoped list, demonstrating isolation + the client-role narrowing."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.db import models as m
from server.domain.enums import UserRole

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("")
def list_clients(
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(require(Permission.CLIENTS_READ)),
) -> list:
    # Tenant isolation is automatic (the scoped session filters by tenant_id). A client-role user is
    # further narrowed to its own importer.
    stmt = select(m.Client)
    if principal.role is UserRole.client and principal.client_scope_id:
        stmt = stmt.where(m.Client.id == principal.client_scope_id)
    return [
        {"id": c.id, "name": c.name, "importer_id": c.importer_id}
        for c in db.scalars(stmt).all()
    ]
