"""M2 — password hashing (argon2) and JWT access tokens."""
from __future__ import annotations

import time

import jwt
import pytest

from server.auth import tokens
from server.auth.passwords import hash_password, verify_password


def test_password_hash_roundtrip():
    secret = "correct horse battery staple"
    hashed = hash_password(secret)
    assert hashed != secret                       # never store plaintext
    assert verify_password(hashed, secret)
    assert not verify_password(hashed, "wrong")
    assert not verify_password("not-a-valid-hash", "x")  # bad hash → False, never raises


def test_jwt_roundtrip_carries_claims():
    token = tokens.create_access_token("user-1", {"tenant": "tenant-A", "role": "signer"})
    payload = tokens.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant"] == "tenant-A"
    assert payload["role"] == "signer"


def test_jwt_tampered_token_is_rejected():
    token = tokens.create_access_token("u", {"tenant": "A", "role": "admin"})
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(jwt.PyJWTError):
        tokens.decode_token(tampered)


def test_jwt_expired_token_is_rejected():
    issued_long_ago = int(time.time()) - 10_000
    token = tokens.create_access_token(
        "u", {"tenant": "A", "role": "admin"}, ttl_seconds=1, now=issued_long_ago
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        tokens.decode_token(token)
