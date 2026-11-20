"""Shared test fixtures.

Tests never read your .env and never touch data/inventory.db: each test gets a
fresh app wired to its own settings.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fakes import FakeNotifier


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # ignore any local .env
        secret_key="test-secret-key-that-is-long-enough",
        database_url="sqlite://",  # in-memory
        log_level="WARNING",
    )


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def app(settings, notifier):
    return create_app(settings, notifier=notifier)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db(app):
    """A session on the same database the app uses, for arranging test data."""
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def user(db):
    from app.services.auth_service import create_user

    return create_user(db, "mum", "correct-horse-battery")


@pytest.fixture
def auth_headers(client, user) -> dict:
    resp = client.post(
        "/api/auth/login", json={"username": "mum", "password": "correct-horse-battery"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
