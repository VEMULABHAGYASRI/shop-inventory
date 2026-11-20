"""Database engine and session setup (SQLAlchemy 2.0)."""
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Parent class for all ORM models."""


def make_engine(database_url: str) -> Engine:
    kwargs: dict = {}
    if database_url.startswith("sqlite"):
        # FastAPI may run a request on a different thread than the one that
        # opened the connection; SQLite needs to be told that's OK.
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            # An in-memory DB lives inside one connection. StaticPool reuses
            # that single connection so every session sees the same data.
            kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **kwargs)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_conn, _record):
            # SQLite ignores FOREIGN KEY constraints unless asked per connection.
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create any tables that don't exist yet.

    Fine for a small app. If you later need to *change* existing tables
    without losing data, add a migration tool such as Alembic.
    """
    import app.models  # noqa: F401  (registers the models on Base)

    Base.metadata.create_all(engine)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
