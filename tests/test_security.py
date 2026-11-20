"""Unit tests for the pure security helpers (no app, no database)."""
from app.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)


def test_password_hash_roundtrip():
    stored = hash_password("s3cret-pass")
    assert "s3cret-pass" not in stored
    assert verify_password("s3cret-pass", stored)
    assert not verify_password("wrong", stored)


def test_same_password_gets_different_salts():
    assert hash_password("same") != hash_password("same")


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-real-hash") is False


def test_session_tokens_are_random_and_long():
    tokens = {new_session_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 40 for t in tokens)


def test_token_fingerprint_is_stable_and_not_the_token():
    token = new_session_token()
    assert hash_session_token(token) == hash_session_token(token)
    assert token not in hash_session_token(token)
