from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import AuthenticationError, ConflictError, NotFoundError
from app.logging_config import get_logger
from app.models import LoginSession, User
from app.models._common import utcnow
from app.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)

logger = get_logger("auth")

# Used when the username doesn't exist, so a failed login takes the same time
# either way (otherwise response timing could reveal which usernames exist).
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_user(db: Session, username: str, password: str) -> User:
    username = username.strip().lower()
    if db.scalar(select(User).where(User.username == username)):
        raise ConflictError(f"Username '{username}' is already taken")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    logger.info("Created user %s (id=%s)", user.username, user.id)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        ok = False
    else:
        ok = verify_password(password, user.password_hash)
    if not ok:
        logger.warning("Failed login for username %r", username)
        raise AuthenticationError("Incorrect username or password")
    logger.info("User %s logged in", user.username)
    return user


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username)))


def _as_utc(value: datetime) -> datetime:
    # SQLite hands datetimes back without a timezone; we always store UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def start_session(db: Session, user: User, expire_minutes: int) -> str:
    """Log a user in. Returns the token to give to the browser."""
    now = utcnow()
    # Housekeeping: drop sessions that have expired, so the table stays small.
    db.execute(delete(LoginSession).where(LoginSession.expires_at < now))
    token = new_session_token()
    db.add(LoginSession(token_hash=hash_session_token(token), user_id=user.id,
                        expires_at=now + timedelta(minutes=expire_minutes)))
    db.commit()
    return token


def user_for_token(db: Session, token: str) -> User:
    """Return the logged-in user for a token, or raise AuthenticationError."""
    session = db.scalar(
        select(LoginSession).where(LoginSession.token_hash == hash_session_token(token))
    )
    if session is None:
        raise AuthenticationError("Not logged in")
    if _as_utc(session.expires_at) <= utcnow():
        db.delete(session)
        db.commit()
        raise AuthenticationError("Your session has expired, please log in again")
    return session.user


def end_session(db: Session, token: str) -> None:
    """Log out: the token stops working immediately."""
    db.execute(delete(LoginSession).where(LoginSession.token_hash == hash_session_token(token)))
    db.commit()
