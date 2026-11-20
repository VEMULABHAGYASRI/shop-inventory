import pytest
from pydantic import ValidationError

from app.config import Settings


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert len(resp.headers["X-Request-ID"]) == 8


def test_unknown_route_uses_standard_error_format(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["request_id"] == resp.headers["X-Request-ID"]


@pytest.mark.parametrize("bad_key", ["change-me", "short"])
def test_settings_reject_weak_secret_key(bad_key):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key=bad_key)


def test_web_ui_is_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<title>Shop Inventory</title>" in resp.text
    assert client.get("/app.js").status_code == 200
