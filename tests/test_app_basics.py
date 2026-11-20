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


def test_web_ui_is_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<title>Shop Inventory</title>" in resp.text
    assert client.get("/app.js").status_code == 200


def test_runs_with_no_configuration(monkeypatch, tmp_path):
    """No .env and no environment variables: defaults must be enough."""
    from app.config import Settings

    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.database_url.startswith("sqlite")
    assert settings.low_stock_webhook_url == ""
