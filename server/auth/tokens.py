"""JWT access tokens (HS256, PyJWT).

The signing secret comes from ``DRAWBACK_JWT_SECRET`` — no secret is committed. If it is unset (dev/
test), a per-process random secret is generated: tokens work for the life of the process and are
invalidated on restart, which is fine for development but must NOT be relied on in production (set the
env var). Tokens carry the user id (``sub``) plus the tenant/role/client-scope claims the API needs to
build a :class:`~server.auth.context.Principal` without a database hit.
"""
from __future__ import annotations

import os
import secrets
import time
from typing import Optional

import jwt

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 12 * 3600

_ephemeral_secret: Optional[str] = None


def _secret() -> str:
    configured = os.environ.get("DRAWBACK_JWT_SECRET")
    if configured:
        return configured
    global _ephemeral_secret
    if _ephemeral_secret is None:
        _ephemeral_secret = secrets.token_urlsafe(48)
    return _ephemeral_secret


def create_access_token(
    subject: str,
    claims: Optional[dict] = None,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: Optional[int] = None,
) -> str:
    issued = int(now if now is not None else time.time())
    payload = {"sub": subject, "iat": issued, "exp": issued + ttl_seconds}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode + verify (signature & expiry). Raises ``jwt.PyJWTError`` on any problem."""
    return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
