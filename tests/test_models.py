"""Database-level safety nets, tested without going through the API."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.database import init_db, make_engine, make_session_factory
from app.models import Item


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    init_db(engine)
    with make_session_factory(engine)() as s:
        yield s


def test_database_rejects_negative_quantity(session):
    session.add(Item(sku="X1", name="Thing", quantity=-1))
    with pytest.raises(IntegrityError):
        session.commit()


def test_sku_must_be_unique(session):
    session.add(Item(sku="X1", name="A"))
    session.commit()
    session.add(Item(sku="X1", name="B"))
    with pytest.raises(IntegrityError):
        session.commit()
