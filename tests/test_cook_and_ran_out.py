import pytest

from app.db import get_connection, sync_canonical_ingredients


@pytest.fixture(autouse=True, scope="session")
def _seed():
    sync_canonical_ingredients()


@pytest.fixture(autouse=True)
def _clean_slate():
    conn = get_connection()
    for table in ["shopping_item", "cook_log", "recipe_ingredient", "recipe_step", "recipe", "pantry_item"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def _make_recipe(conn, have_names, missing_names, title="Test Recipe"):
    from app.ingredients import resolve_ingredient_id

    cur = conn.execute(
        "INSERT INTO recipe (title, base_servings, cuisine, est_minutes, keeps_well) VALUES (?, 2, 'Test', 20, 0)",
        (title,),
    )
    recipe_id = cur.lastrowid
    for name in have_names:
        ing_id = resolve_ingredient_id(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO pantry_item (ingredient_id, qty_label) VALUES (?, '')", (ing_id,)
        )
        conn.execute(
            "INSERT INTO recipe_ingredient (recipe_id, ingredient_id) VALUES (?, ?)",
            (recipe_id, ing_id),
        )
    for name in missing_names:
        ing_id = resolve_ingredient_id(conn, name)
        conn.execute(
            "INSERT INTO recipe_ingredient (recipe_id, ingredient_id, qty, unit) VALUES (?, ?, '1', 'tbsp')",
            (recipe_id, ing_id),
        )
    conn.commit()
    return recipe_id


def test_cook_logs_and_returns_used_pantry_items(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Chicken thighs", "Rice"], ["Soy sauce"])
    conn.close()

    resp = auth_client.post(f"/api/recipes/{recipe_id}/cook")
    assert resp.status_code == 201
    body = resp.json()
    assert body["recipe_id"] == recipe_id
    names = {u["name"] for u in body["used_pantry_items"]}
    assert names == {"Chicken thighs", "Rice"}

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM cook_log WHERE recipe_id = ?", (recipe_id,)).fetchone()
    conn.close()
    assert count["c"] == 1


def test_cook_unknown_recipe_404(auth_client):
    assert auth_client.post("/api/recipes/999999/cook").status_code == 404


def test_ran_out_moves_pantry_item_to_shopping_list(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Garlic"], [])
    item = conn.execute(
        "SELECT pantry_item.id FROM pantry_item JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id WHERE canonical_ingredient.name = 'Garlic'"
    ).fetchone()
    pantry_item_id = item["id"]
    conn.close()

    resp = auth_client.post("/api/pantry/ran-out", json={"pantry_item_ids": [pantry_item_id]})
    assert resp.status_code == 200
    assert resp.json()["moved"][0]["name"] == "Garlic"

    pantry = auth_client.get("/api/pantry").json()
    assert all(p["id"] != pantry_item_id for p in pantry)

    conn = get_connection()
    shopping_count = conn.execute(
        """
        SELECT COUNT(*) AS c FROM shopping_item
        JOIN canonical_ingredient ON canonical_ingredient.id = shopping_item.ingredient_id
        WHERE canonical_ingredient.name = 'Garlic' AND shopping_item.added_from = 'ran_out'
        """
    ).fetchone()
    conn.close()
    assert shopping_count["c"] == 1


def test_ran_out_does_not_duplicate_existing_shopping_entry(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Ginger"], [])
    ing = conn.execute("SELECT id FROM canonical_ingredient WHERE name = 'Ginger'").fetchone()
    conn.execute("INSERT INTO shopping_item (ingredient_id, added_from) VALUES (?, 'manual')", (ing["id"],))
    item = conn.execute(
        "SELECT id FROM pantry_item WHERE ingredient_id = ?", (ing["id"],)
    ).fetchone()
    conn.commit()
    conn.close()

    auth_client.post("/api/pantry/ran-out", json={"pantry_item_ids": [item["id"]]})

    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM shopping_item WHERE ingredient_id = ?", (ing["id"],)
    ).fetchone()
    conn.close()
    assert count["c"] == 1


def test_add_missing_ingredient_to_shopping_list_then_recipe_reflects_it(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, [], ["Test Missing Thing"])
    conn.close()

    detail = auth_client.get(f"/api/recipes/{recipe_id}").json()
    missing = next(i for i in detail["ingredients"] if i["name"] == "Test Missing Thing")
    assert missing["on_shopping_list"] is False

    resp = auth_client.post("/api/shopping", json={"ingredient_id": missing["ingredient_id"]})
    assert resp.status_code == 201
    assert resp.json()["on_list"] is True

    # Idempotent — adding again doesn't create a second row.
    auth_client.post("/api/shopping", json={"ingredient_id": missing["ingredient_id"]})
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM shopping_item WHERE ingredient_id = ?", (missing["ingredient_id"],)
    ).fetchone()
    conn.close()
    assert count["c"] == 1

    detail2 = auth_client.get(f"/api/recipes/{recipe_id}").json()
    missing2 = next(i for i in detail2["ingredients"] if i["name"] == "Test Missing Thing")
    assert missing2["on_shopping_list"] is True


def test_shopping_unknown_ingredient_404(auth_client):
    assert auth_client.post("/api/shopping", json={"ingredient_id": 999999}).status_code == 404


def test_cook_and_shopping_require_auth(client):
    assert client.post("/api/recipes/1/cook").status_code == 404
    assert client.post("/api/pantry/ran-out", json={"pantry_item_ids": []}).status_code == 404
    assert client.post("/api/shopping", json={"ingredient_id": 1}).status_code == 404


def test_rate_cook_log(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Garlic"], [])
    conn.close()

    cook = auth_client.post(f"/api/recipes/{recipe_id}/cook").json()

    resp = auth_client.post(f"/api/cook-log/{cook['cook_log_id']}/rate", json={"rating": 4})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    conn = get_connection()
    rating = conn.execute(
        "SELECT rating FROM cook_log WHERE id = ?", (cook["cook_log_id"],)
    ).fetchone()
    conn.close()
    assert rating["rating"] == 4


def test_rate_cook_log_rejects_out_of_range(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Garlic"], [])
    conn.close()
    cook = auth_client.post(f"/api/recipes/{recipe_id}/cook").json()

    resp = auth_client.post(f"/api/cook-log/{cook['cook_log_id']}/rate", json={"rating": 6})
    assert resp.status_code == 422


def test_rate_unknown_cook_log_404(auth_client):
    assert auth_client.post("/api/cook-log/999999/rate", json={"rating": 3}).status_code == 404


def test_rate_cook_log_requires_auth(client):
    assert client.post("/api/cook-log/1/rate", json={"rating": 3}).status_code == 404


def test_tenth_cook_dispatches_rewrite_profile_job(auth_client):
    conn = get_connection()
    recipe_id = _make_recipe(conn, ["Garlic"], [])
    for _ in range(9):
        conn.execute("INSERT INTO cook_log (recipe_id) VALUES (?)", (recipe_id,))
    conn.commit()
    conn.execute("DELETE FROM job")
    conn.commit()
    conn.close()

    auth_client.post(f"/api/recipes/{recipe_id}/cook")

    conn = get_connection()
    jobs = conn.execute("SELECT kind FROM job").fetchall()
    conn.close()
    assert [j["kind"] for j in jobs] == ["rewrite_profile"]
