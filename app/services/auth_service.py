from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AuthenticationError, ConflictError, NotFoundError
from app.logging_config import get_logger
from app.models import User
from app.security import hash_password, verify_password

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
