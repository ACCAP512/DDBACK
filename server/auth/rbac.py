"""Role-based access control — the permission each role carries.

Roles (BUILD_PLAN §5): **Admin · Preparer · Reviewer · Signer · Client (read-only)**. The licensed-
filer sign-off gate maps to ``claims:sign``, held only by the **Signer** (and Admin) — so no preparer,
reviewer, or client can finalize a claim. The ``client`` role is read-only and additionally scoped to
its one importer at the data-access layer.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

from server.domain.enums import UserRole


class Permission(str, Enum):
    CLIENTS_READ = "clients:read"
    CLIENTS_WRITE = "clients:write"
    PROGRAMS_READ = "programs:read"
    PROGRAMS_WRITE = "programs:write"
    CLAIMS_READ = "claims:read"
    CLAIMS_WRITE = "claims:write"
    CLAIMS_SIGN = "claims:sign"        # the licensed-filer sign-off gate
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    USERS_MANAGE = "users:manage"


_ALL: FrozenSet[Permission] = frozenset(Permission)

ROLE_PERMISSIONS: Dict[UserRole, FrozenSet[Permission]] = {
    UserRole.admin: _ALL,
    UserRole.preparer: frozenset({
        Permission.CLIENTS_READ, Permission.PROGRAMS_READ, Permission.PROGRAMS_WRITE,
        Permission.CLAIMS_READ, Permission.CLAIMS_WRITE,
        Permission.DOCUMENTS_READ, Permission.DOCUMENTS_WRITE,
    }),
    UserRole.reviewer: frozenset({
        Permission.CLIENTS_READ, Permission.PROGRAMS_READ,
        Permission.CLAIMS_READ, Permission.DOCUMENTS_READ,
    }),
    UserRole.signer: frozenset({
        Permission.CLIENTS_READ, Permission.PROGRAMS_READ,
        Permission.CLAIMS_READ, Permission.CLAIMS_SIGN, Permission.DOCUMENTS_READ,
    }),
    UserRole.client: frozenset({
        Permission.CLIENTS_READ, Permission.CLAIMS_READ, Permission.DOCUMENTS_READ,
    }),
}


def permissions_for(role: UserRole) -> FrozenSet[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in permissions_for(role)
