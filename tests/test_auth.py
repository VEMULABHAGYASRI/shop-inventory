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
