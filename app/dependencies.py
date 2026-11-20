"""FastAPI dependencies: small functions routes declare as parameters.

They read shared objects from `app.state` (set up in main.create_app), which
is what lets tests swap in a different database or notifier.
"""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import session_scope


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)
