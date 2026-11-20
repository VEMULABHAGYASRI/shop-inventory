from sqlalchemy import select

from app.cli import main
from app.database import make_engine, make_session_factory
from app.models import User


def _settings(tmp_path):
    from app.config import Settings

    return Settings(
        _env_file=None,
        secret_key="test-secret-key-that-is-long-enough",
        database_url=f"sqlite:///{tmp_path}/cli.db",
    )


def test_create_user_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "a-good-password")
    settings = _settings(tmp_path)

    assert main(["create-user", "Mum"], settings) == 0
    assert "Created user 'mum'" in capsys.readouterr().out

    with make_session_factory(make_engine(settings.database_url))() as db:
        assert db.scalar(select(User.username)) == "mum"


def test_create_user_rejects_short_password(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "short")
    assert main(["create-user", "mum"], _settings(tmp_path)) == 1
    assert "password" in capsys.readouterr().err
