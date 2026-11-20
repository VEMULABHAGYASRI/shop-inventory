"""Password hashing and login tokens. Pure functions, no database access.

Passwords: hashed with scrypt (Python standard library), a slow, memory-hard
algorithm designed for passwords, with a random salt per user. The stored
string records its own parameters, so they can be raised later without
breaking existing hashes.

Tokens: JSON Web Tokens signed with INVENTORY_SECRET_KEY. Anyone can *read* a
JWT, but nobody can create or alter one without the key.
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.errors import AuthenticationError

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
_ALGORITHM = "HS256"


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


def create_access_token(user_id: int, secret_key: str, expire_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=expire_minutes)}
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> int:
    """Return the user id inside a valid token, or raise AuthenticationError."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Your session has expired, please log in again")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise AuthenticationError("Invalid authentication token")
