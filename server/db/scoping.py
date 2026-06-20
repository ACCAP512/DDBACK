"""Structural tenant isolation at the data-access layer (BUILD_PLAN §5, M2).

Rather than trust every query to remember a ``WHERE tenant_id = ...`` (route discipline), this installs
a SQLAlchemy ``do_orm_execute`` hook that injects that predicate into **every ORM SELECT** for every
tenant-owned model, via ``with_loader_criteria`` — so a forgotten filter cannot leak another tenant's
rows. A session only gets filtered once a :class:`~server.auth.context.Principal` is bound to it
(:func:`bind_principal`); unscoped/system sessions (the engine seam, migrations, login) are unaffected,
and a query can explicitly opt out with ``.execution_options(skip_tenant_filter=True)``.

This is why every tenant-owned table carries a ``tenant_id`` (denormalized onto Program/Claim/
ChecklistItem in M2): one uniform predicate covers them all.
"""
from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from server.auth.context import Principal
from server.db import models as m

_PRINCIPAL_KEY = "principal"
SKIP_OPTION = "skip_tenant_filter"

# Every model with a tenant_id column. Tenant itself is the boundary and is not row-filtered here.
TENANT_OWNED: Tuple[type, ...] = (
    m.User, m.Client, m.Program, m.Claim, m.ImportEntryLine, m.ExportLine,
    m.Designation, m.Document, m.ChecklistItem, m.Task, m.AuditEvent,
)


def bind_principal(session: Session, principal: Principal) -> None:
    """Scope every subsequent ORM SELECT on ``session`` to ``principal.tenant_id``."""
    session.info[_PRINCIPAL_KEY] = principal


def principal_of(session: Session) -> Optional[Principal]:
    return session.info.get(_PRINCIPAL_KEY)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_isolation(state: ORMExecuteState) -> None:
    if not state.is_select or state.execution_options.get(SKIP_OPTION):
        return
    principal = state.session.info.get(_PRINCIPAL_KEY)
    if principal is None:
        return
    tenant_id = principal.tenant_id
    state.statement = state.statement.options(
        *[
            with_loader_criteria(model, lambda cls: cls.tenant_id == tenant_id, include_aliases=True)
            for model in TENANT_OWNED
        ]
    )
