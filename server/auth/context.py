"""The authenticated principal — the identity + scope every request is evaluated against."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from server.domain.enums import UserRole


@dataclass(frozen=True)
class Principal:
    """Who is making the request and what they're scoped to. Built from a verified JWT; the
    ``tenant_id`` drives row-level isolation and ``client_scope_id`` (set only for the ``client`` role)
    narrows a client-portal user to a single importer."""

    user_id: str
    tenant_id: str
    role: UserRole
    client_scope_id: Optional[str] = None
