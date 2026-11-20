"""Password hashing and login tokens. Pure functions, no database access.

Passwords: hashed with scrypt (Python standard library), a slow, memory-hard
algorithm designed for passwords, with a random salt per user. The stored
string records its own parameters, so they can be raised later without
breaking existing hashes.

Login tokens: 256 random bits from the `secrets` module. Unguessable, so no
signing key is needed; the server simply looks them up (see auth_service).
Only their SHA-256 fingerprint is stored.
"""
import base64
import hashlib
import hmac
import secrets

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, digest_b64 = stored.split("$")
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt_b64),
            n=int(n), r=int(r), p=int(p),
        )
    except (ValueError, TypeError):
        return False
    # Constant-time comparison: doesn't leak how many bytes matched.
    return hmac.compare_digest(actual, expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    # A plain fast hash is right here (unlike passwords): the token is
    # already 256 random bits, so there is nothing to brute-force.
    return hashlib.sha256(token.encode()).hexdigest()
