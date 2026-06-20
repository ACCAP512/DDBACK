"""User provisioning + authentication."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.auth.context import Principal
from server.auth.passwords import hash_password, verify_password
from server.db.models import User
from server.domain.enums import UserRole


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(
    session: Session,
    *,
    tenant_id: str,
    email: str,
    password: str,
    name: str,
    role: UserRole,
    client_scope_id: Optional[str] = None,
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=_normalize_email(email),
        password_hash=hash_password(password),
        name=name,
        role=role,
        client_scope_id=client_scope_id,
        active=True,
    )
    session.add(user)
    session.flush()
    return user


def authenticate(session: Session, *, email: str, password: str) -> Optional[User]:
    """Return the user iff the email+password match an active account, else None.

    Login is pre-tenant-context, so the lookup spans tenants (and bypasses the tenant filter — there is
    no principal yet). Emails are unique *per tenant*; if two tenants share one, login is ambiguous and
    rejected — a production deployment would disambiguate with an org selector.
    """
    users = session.scalars(
        select(User)
        .where(User.email == _normalize_email(email))
        .execution_options(skip_tenant_filter=True)
    ).all()
    if len(users) != 1:
        return None
    user = users[0]
    if not user.active or not verify_password(user.password_hash, password):
        return None
    return user


def principal_for(user: User) -> Principal:
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        client_scope_id=user.client_scope_id,
    )
