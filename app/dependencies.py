"""FastAPI dependencies: small functions routes declare as parameters.

They read shared objects from `app.state` (set up in main.create_app), which
is what lets tests swap in a different database or notifier.
"""
from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import session_scope
from app.errors import AuthenticationError
from app.models import User
from app.security import decode_access_token


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Add `user: User = Depends(get_current_user)` to a route to require login."""
    if credentials is None:
        raise AuthenticationError("Not logged in")
    settings: Settings = request.app.state.settings
    user_id = decode_access_token(credentials.credentials, settings.secret_key)
    user = db.get(User, user_id)
    if user is None:  # token for a user that was deleted
        raise AuthenticationError("Invalid authentication token")
    return user
