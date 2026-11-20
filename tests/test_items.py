import pytest

RICE = {"sku": "rice-5kg ", "name": "Basmati rice 5kg", "category": "Grains",
        "reorder_level": 3, "unit_price_cents": 1299}


@pytest.fixture
def rice(client, auth_headers) -> dict:
    resp = client.post("/api/items", json=RICE, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_items_require_login(client):
    assert client.get("/api/items").status_code == 401


def test_create_item_normalizes_sku(rice):
    assert rice["sku"] == "RICE-5KG"
    assert rice["quantity"] == 0
    assert rice["is_low_stock"] is True  # 0 <= reorder level 3


def test_duplicate_sku_conflict(client, auth_headers, rice):
    resp = client.post("/api/items", json={**RICE, "sku": "RICE-5KG"}, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.parametrize("bad", [
    {"name": ""},
    {"unit_price_cents": -1},
    {"reorder_level": -5},
    {"sku": "has/slash"},
    {"unit_price_cents": "free"},
])
def test_create_item_validation(client, auth_headers, bad):
    resp = client.post("/api/items", json={**RICE, **bad}, headers=auth_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["field"] == next(iter(bad))


def test_quantity_cannot_be_set_directly(client, auth_headers, rice):
    resp = client.patch(f"/api/items/{rice['id']}", json={"quantity": 999}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 0  # unknown field ignored


def test_get_missing_item(client, auth_headers):
    resp = client.get("/api/items/999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["message"] == "Item 999 not found"


def test_partial_update(client, auth_headers, rice):
    resp = client.patch(f"/api/items/{rice['id']}", json={"name": "Rice 5kg"}, headers=auth_headers)
    assert resp.json()["name"] == "Rice 5kg"
    assert resp.json()["category"] == "Grains"  # untouched


def test_update_can_clear_category(client, auth_headers, rice):
    resp = client.patch(f"/api/items/{rice['id']}", json={"category": None}, headers=auth_headers)
    assert resp.json()["category"] is None


def test_update_to_taken_sku_conflicts(client, auth_headers, rice):
    client.post("/api/items", json={**RICE, "sku": "OIL-1L", "name": "Oil"}, headers=auth_headers)
    resp = client.patch(f"/api/items/{rice['id']}", json={"sku": "oil-1l"}, headers=auth_headers)
    assert resp.status_code == 409


def test_delete_item(client, auth_headers, rice):
    assert client.delete(f"/api/items/{rice['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/items/{rice['id']}", headers=auth_headers).status_code == 404


def test_search_filter_and_categories(client, auth_headers, rice):
    client.post("/api/items", json={"sku": "OIL-1L", "name": "Sunflower oil", "category": "Oils",
                                    "reorder_level": 0}, headers=auth_headers)

    def names(**params):
        resp = client.get("/api/items", params=params, headers=auth_headers)
        return [i["name"] for i in resp.json()]

    assert names(search="sunflower") == ["Sunflower oil"]
    assert names(search="RICE") == ["Basmati rice 5kg"]
    assert names(search="%") == []  # treated as literal text
    assert names(category="Grains") == ["Basmati rice 5kg"]
    assert len(names(low_stock=True)) == 2  # both have quantity 0
    cats = client.get("/api/categories", headers=auth_headers).json()
    assert cats == ["Grains", "Oils"]
