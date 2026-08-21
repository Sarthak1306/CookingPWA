import pytest

from app.db import get_connection, sync_canonical_ingredients


@pytest.fixture(autouse=True, scope="session")
def _seed():
    sync_canonical_ingredients()


@pytest.fixture(autouse=True)
def _clean_slate():
    conn = get_connection()
    for table in ["shopping_item", "pantry_item"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def test_manual_add_by_name_creates_ingredient_and_lists_it(auth_client):
    resp = auth_client.post("/api/shopping", json={"name": "Test New Thing", "added_from": "manual"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test New Thing"
    assert resp.json()["on_list"] is True

    listing = auth_client.get("/api/shopping").json()
    assert any(i["name"] == "Test New Thing" for i in listing)


def test_manual_add_missing_name_and_id_400(auth_client):
    assert auth_client.post("/api/shopping", json={}).status_code == 400


def test_manual_add_by_name_is_idempotent(auth_client):
    auth_client.post("/api/shopping", json={"name": "Test Repeat Thing"})
    auth_client.post("/api/shopping", json={"name": "test repeat thing"})  # case-insensitive match
    listing = auth_client.get("/api/shopping").json()
    assert sum(1 for i in listing if i["name"] == "Test Repeat Thing") == 1


def test_tick_off_creates_pantry_item_at_pack_size(auth_client):
    added = auth_client.post("/api/shopping", json={"name": "Garlic"}).json()
    shopping_item_id = auth_client.get("/api/shopping").json()[0]["id"]

    resp = auth_client.post(f"/api/shopping/{shopping_item_id}/tick")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Garlic"
    assert body["ingredient_id"] == added["ingredient_id"]
    assert body["qty_label"]  # pack size, non-empty for a known fixture ingredient

    listing = auth_client.get("/api/shopping").json()
    assert listing == []

    conn = get_connection()
    pantry_row = conn.execute(
        "SELECT qty_label, is_low FROM pantry_item WHERE ingredient_id = ?", (added["ingredient_id"],)
    ).fetchone()
    conn.close()
    assert pantry_row is not None
    assert pantry_row["is_low"] == 0
    assert pantry_row["qty_label"] == body["qty_label"]


def test_tick_off_merges_into_existing_pantry_item(auth_client):
    conn = get_connection()
    from app.ingredients import resolve_ingredient_id

    ing_id = resolve_ingredient_id(conn, "Ginger")
    conn.execute(
        "INSERT INTO pantry_item (ingredient_id, qty_label, is_low) VALUES (?, 'a sliver', 1)", (ing_id,)
    )
    existing_pantry_item_id = conn.execute(
        "SELECT id FROM pantry_item WHERE ingredient_id = ?", (ing_id,)
    ).fetchone()["id"]
    conn.execute("INSERT INTO shopping_item (ingredient_id, added_from) VALUES (?, 'ran_out')", (ing_id,))
    shopping_item_id = conn.execute(
        "SELECT id FROM shopping_item WHERE ingredient_id = ?", (ing_id,)
    ).fetchone()["id"]
    conn.commit()
    conn.close()

    resp = auth_client.post(f"/api/shopping/{shopping_item_id}/tick")
    assert resp.status_code == 200

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM pantry_item WHERE ingredient_id = ?", (ing_id,)).fetchone()
    row = conn.execute("SELECT id, qty_label, is_low FROM pantry_item WHERE ingredient_id = ?", (ing_id,)).fetchone()
    conn.close()
    assert count["c"] == 1  # merged, not duplicated
    assert row["id"] == existing_pantry_item_id
    assert row["is_low"] == 0
    assert row["qty_label"] != "a sliver"


def test_tick_unknown_shopping_item_404(auth_client):
    assert auth_client.post("/api/shopping/999999/tick").status_code == 404


def test_remove_shopping_item_does_not_touch_pantry(auth_client):
    auth_client.post("/api/shopping", json={"name": "Test Remove Me"})
    shopping_item_id = auth_client.get("/api/shopping").json()[0]["id"]

    resp = auth_client.delete(f"/api/shopping/{shopping_item_id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    assert auth_client.get("/api/shopping").json() == []

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM pantry_item").fetchone()
    conn.close()
    assert count["c"] == 0


def test_remove_unknown_shopping_item_404(auth_client):
    assert auth_client.delete("/api/shopping/999999").status_code == 404


def test_shopping_list_requires_auth(client):
    assert client.get("/api/shopping").status_code == 404
    assert client.post("/api/shopping/1/tick").status_code == 404
    assert client.delete("/api/shopping/1").status_code == 404
