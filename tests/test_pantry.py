import pytest

from app.db import get_connection, sync_canonical_ingredients


@pytest.fixture(autouse=True, scope="session")
def _seed():
    sync_canonical_ingredients()


@pytest.fixture(autouse=True)
def _empty_pantry():
    conn = get_connection()
    conn.execute("DELETE FROM pantry_item")
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def test_pantry_requires_auth(client):
    assert client.get("/api/pantry").status_code == 404


def test_add_item_only_needs_a_name(auth_client):
    resp = auth_client.post("/api/pantry", json={"name": "Lemons"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Lemons"
    assert body["category"] == "Produce"


def test_add_item_with_unknown_name_creates_canonical_ingredient(auth_client):
    resp = auth_client.post("/api/pantry", json={"name": "Nutritional yeast"})
    assert resp.status_code == 201
    assert resp.json()["category"] == "Other"


def test_adding_same_name_twice_updates_in_place(auth_client):
    first = auth_client.post("/api/pantry", json={"name": "Garlic", "qty_label": "bulb"}).json()
    second = auth_client.post(
        "/api/pantry", json={"name": "garlic", "qty_label": "half a bulb"}
    ).json()

    assert first["id"] == second["id"]
    assert second["qty_label"] == "half a bulb"
    assert len(auth_client.get("/api/pantry").json()) == 1


def test_restock_clears_low_flag_and_sets_pack_label(auth_client):
    item = auth_client.post(
        "/api/pantry", json={"name": "Milk", "qty_label": "nearly empty", "is_low": True}
    ).json()

    restocked = auth_client.post(f"/api/pantry/{item['id']}/restock").json()
    assert restocked["is_low"] is False
    assert restocked["qty_label"] == restocked["pack"]


def test_editing_name_to_a_different_existing_ingredient_merges(auth_client):
    milk = auth_client.post("/api/pantry", json={"name": "Milk"}).json()
    auth_client.post("/api/pantry", json={"name": "Oat milk", "qty_label": "1L"})

    merged = auth_client.patch(
        f"/api/pantry/{milk['id']}", json={"name": "Oat milk", "qty_label": "2L carton"}
    ).json()

    pantry = auth_client.get("/api/pantry").json()
    assert len(pantry) == 1
    assert pantry[0]["name"] == "Oat milk"
    assert pantry[0]["qty_label"] == "2L carton"
    assert merged["id"] == pantry[0]["id"]


def test_ingredient_autocomplete(auth_client):
    resp = auth_client.get("/api/ingredients", params={"q": "chick"})
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "Chicken thighs" in names


def test_autocomplete_empty_query_returns_nothing(auth_client):
    assert auth_client.get("/api/ingredients", params={"q": ""}).json() == []
