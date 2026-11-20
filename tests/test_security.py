"""Unit tests for the pure security helpers (no app, no database)."""
import pytest

from app.errors import AuthenticationError
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

KEY = "unit-test-secret-key-long-enough"


def test_password_hash_roundtrip():
    stored = hash_password("s3cret-pass")
    assert "s3cret-pass" not in stored
    assert verify_password("s3cret-pass", stored)
    assert not verify_password("wrong", stored)


def test_same_password_gets_different_salts():
    assert hash_password("same") != hash_password("same")


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-real-hash") is False


def test_token_roundtrip():
    token = create_access_token(42, KEY, expire_minutes=5)
    assert decode_access_token(token, KEY) == 42


def test_expired_token_rejected():
    token = create_access_token(42, KEY, expire_minutes=-1)
    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(token, KEY)


def test_token_signed_with_other_key_rejected():
    token = create_access_token(42, "another-secret-key-that-is-long-enough", 5)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, KEY)
