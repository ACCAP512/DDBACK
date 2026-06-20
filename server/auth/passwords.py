"""Password hashing — argon2id via argon2-cffi (the modern memory-hard KDF).

Plaintext passwords are never stored; only the argon2 hash (which embeds its own salt + parameters)
goes in ``User.password_hash``. Verification is constant-time within argon2.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # library defaults (argon2id, sensible memory/time cost)


def hash_password(plaintext: str) -> str:
    return _hasher.hash(plaintext)


def verify_password(hashed: str, plaintext: str) -> bool:
    """True iff ``plaintext`` matches ``hashed``. Never raises on a bad password/hash — returns False."""
    try:
        return _hasher.verify(hashed, plaintext)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the stored hash used weaker parameters than the current policy (rehash on next login)."""
    return _hasher.check_needs_rehash(hashed)
