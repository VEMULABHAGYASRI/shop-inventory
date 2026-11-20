import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import BrokenNotifier


@pytest.fixture
def item(client, auth_headers) -> dict:
    resp = client.post("/api/items", json={"sku": "MILK", "name": "Milk 1L", "reorder_level": 5,
                                           "initial_quantity": 10}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def move(client, headers, item_id, change, reason, note=None):
    return client.post(f"/api/items/{item_id}/movements",
                       json={"change": change, "reason": reason, "note": note}, headers=headers)


def test_initial_quantity_is_recorded_as_movement(client, auth_headers, item):
    assert item["quantity"] == 10
    history = client.get(f"/api/items/{item['id']}/movements", headers=auth_headers).json()
    assert [(m["change"], m["reason"], m["note"]) for m in history] == [(10, "received", "Initial stock")]


def test_sell_and_receive(client, auth_headers, item):
    resp = move(client, auth_headers, item["id"], -3, "sold")
    assert resp.status_code == 201
    body = resp.json()
    assert body["quantity_after"] == 7
    assert body["user"]["username"] == "mum"
    assert body["item"]["sku"] == "MILK"

    move(client, auth_headers, item["id"], 12, "received", "Tuesday delivery")
    assert client.get(f"/api/items/{item['id']}", headers=auth_headers).json()["quantity"] == 19


def test_cannot_sell_more_than_in_stock(client, auth_headers, item):
    resp = move(client, auth_headers, item["id"], -11, "sold")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "insufficient_stock"
    assert "only 10 in stock" in resp.json()["error"]["message"]
    assert client.get(f"/api/items/{item['id']}", headers=auth_headers).json()["quantity"] == 10


@pytest.mark.parametrize("change,reason", [
    (3, "sold"), (-3, "received"), (0, "adjustment"), (1, "stolen-by-cat"),
])
def test_invalid_movements_rejected(client, auth_headers, item, change, reason):
    resp = move(client, auth_headers, item["id"], change, reason)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_adjustment_can_go_either_way(client, auth_headers, item):
    assert move(client, auth_headers, item["id"], -2, "adjustment").json()["quantity_after"] == 8
    assert move(client, auth_headers, item["id"], 1, "adjustment").json()["quantity_after"] == 9


def test_movement_on_missing_item(client, auth_headers):
    assert move(client, auth_headers, 999, 1, "received").status_code == 404


def test_low_stock_alert_only_when_crossing_threshold(client, auth_headers, item, notifier):
    move(client, auth_headers, item["id"], -4, "sold")  # 10 -> 6: still above 5
    assert notifier.alerts == []

    move(client, auth_headers, item["id"], -1, "sold")  # 6 -> 5: crosses
    assert len(notifier.alerts) == 1
    assert notifier.alerts[0].sku == "MILK"
    assert notifier.alerts[0].quantity == 5

    move(client, auth_headers, item["id"], -1, "sold")  # 5 -> 4: already low, no spam
    assert len(notifier.alerts) == 1

    move(client, auth_headers, item["id"], 10, "received")  # back above
    move(client, auth_headers, item["id"], -10, "sold")     # crosses again
    assert len(notifier.alerts) == 2


def test_failed_rejected_movement_sends_no_alert(client, auth_headers, item, notifier):
    move(client, auth_headers, item["id"], -50, "sold")
    assert notifier.alerts == []


def test_broken_notifier_does_not_break_sales(settings, user):
    app = create_app(settings, notifier=BrokenNotifier())
    with app.state.session_factory() as db:
        from app.services.auth_service import create_user
        create_user(db, "dad", "password-123")
    with TestClient(app) as c:
        token = c.post("/api/auth/login", json={"username": "dad", "password": "password-123"}).json()
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        item = c.post("/api/items", json={"sku": "EGG", "name": "Eggs", "reorder_level": 5,
                                          "initial_quantity": 6}, headers=headers).json()
        resp = move(c, headers, item["id"], -2, "sold")
        assert resp.status_code == 201
        assert resp.json()["quantity_after"] == 4


def test_recent_activity_feed_newest_first(client, auth_headers, item):
    move(client, auth_headers, item["id"], -1, "sold")
    move(client, auth_headers, item["id"], -1, "damaged", "dropped")
    feed = client.get("/api/movements", params={"limit": 2}, headers=auth_headers).json()
    assert [m["reason"] for m in feed] == ["damaged", "sold"]


def test_deleting_item_removes_its_history(client, auth_headers, item):
    client.delete(f"/api/items/{item['id']}", headers=auth_headers)
    assert client.get("/api/movements", headers=auth_headers).json() == []
