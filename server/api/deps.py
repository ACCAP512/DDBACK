"""FastAPI dependencies: DB sessions, the authenticated principal, and permission gating.

``get_db`` yields an unscoped session (used by login). ``get_scoped_db`` binds the request's principal
so the tenant-isolation filter (``server.db.scoping``) applies to every query. ``require(permission)``
gates a route on an RBAC permission. Tests override ``get_db`` to point at a test database; everything
else composes on top of it.
"""
from __future__ import annotations

from typing import Iterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from server.auth import rbac, tokens
from server.auth.context import Principal
from server.db import scoping
from server.db.base import SessionLocal
from server.domain.enums import UserRole

_bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Principal:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        payload = tokens.decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    try:
        return Principal(
            user_id=payload["sub"],
            tenant_id=payload["tenant"],
            role=UserRole(payload["role"]),
            client_scope_id=payload.get("client_scope"),
        )
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed token")


def get_scoped_db(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> Session:
    """A session whose every ORM SELECT is filtered to the principal's tenant."""
    scoping.bind_principal(db, principal)
    return db


def require(permission: rbac.Permission):
    """Dependency factory: 403 unless the principal's role holds ``permission``."""

    def _require(principal: Principal = Depends(get_principal)) -> Principal:
        if not rbac.has_permission(principal.role, permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"role '{principal.role.value}' lacks permission '{permission.value}'",
            )
        return principal

    return _require
