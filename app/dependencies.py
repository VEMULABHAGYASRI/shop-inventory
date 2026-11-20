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
from app.notifications import Notifier
from app.services import auth_service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_notifier(request: Request) -> Notifier:
    return request.app.state.notifier


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


_bearer = HTTPBearer(auto_error=False)


def get_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """The raw token from the `Authorization: Bearer <token>` header."""
    if credentials is None:
        raise AuthenticationError("Not logged in")
    return credentials.credentials


def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)) -> User:
    """Add `user: User = Depends(get_current_user)` to a route to require login."""
    return auth_service.user_for_token(db, token)
