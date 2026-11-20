def test_login_success(client, user):
    resp = client.post("/api/auth/login", json={"username": "MUM ", "password": "correct-horse-battery"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client, user):
    resp = client.post("/api/auth/login", json={"username": "mum", "password": "nope"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_login_unknown_user_gives_same_message(client, user):
    wrong_pw = client.post("/api/auth/login", json={"username": "mum", "password": "nope"})
    no_user = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert wrong_pw.json()["error"]["message"] == no_user.json()["error"]["message"]


def test_login_missing_fields_is_validation_error(client):
    resp = client.post("/api/auth/login", json={"username": "mum"})
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == "password"


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_bad_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_me_returns_user_without_password(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "mum"
    assert "password_hash" not in resp.json()


def test_create_user_requires_login(client):
    resp = client.post("/api/users", json={"username": "dad", "password": "longenough"})
    assert resp.status_code == 401


def test_create_and_list_users(client, auth_headers):
    resp = client.post("/api/users", json={"username": "dad", "password": "longenough"}, headers=auth_headers)
    assert resp.status_code == 201
    names = [u["username"] for u in client.get("/api/users", headers=auth_headers).json()]
    assert names == ["dad", "mum"]


def test_duplicate_username_conflict(client, auth_headers):
    resp = client.post("/api/users", json={"username": "mum", "password": "longenough"}, headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_short_password_rejected(client, auth_headers):
    resp = client.post("/api/users", json={"username": "dad", "password": "short"}, headers=auth_headers)
    assert resp.status_code == 422


def test_logout_revokes_token(client, auth_headers):
    assert client.post("/api/auth/logout", headers=auth_headers).status_code == 204
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 401


def test_two_logins_are_independent(client, user, auth_headers):
    other = client.post("/api/auth/login", json={"username": "mum", "password": "correct-horse-battery"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    client.post("/api/auth/logout", headers=auth_headers)
    assert client.get("/api/auth/me", headers=other_headers).status_code == 200


def test_expired_session_rejected(client, db, auth_headers):
    from datetime import datetime, timezone

    from app.models import LoginSession

    for s in db.query(LoginSession):
        s.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db.commit()
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 401
    assert "expired" in resp.json()["error"]["message"]


def test_database_stores_only_token_fingerprint(client, db, auth_headers):
    from app.models import LoginSession

    token = auth_headers["Authorization"].removeprefix("Bearer ")
    stored = [s.token_hash for s in db.query(LoginSession)]
    assert token not in stored
    assert len(stored) == 1
