"""Shared test fixtures.

Tests never read your .env and never touch data/inventory.db: each test gets a
fresh app wired to its own settings.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # ignore any local .env
        secret_key="test-secret-key-that-is-long-enough",
        database_url="sqlite://",  # in-memory
        log_level="WARNING",
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
