import sqlite3

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_pantry",
            "description": (
                "List everything currently in the pantry. Identity only — no "
                "quantities, since the app never tracks how much of anything "
                "there is. Each item has a pantry_item_id; use that id (not the "
                "name) when reporting which pantry items a recipe uses."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_meals",
            "description": "The last n things cooked, most recent first. Use this to avoid repeating a meal from the last few days.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "how many recent meals to fetch"}},
                "required": ["n"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_taste_profile",
            "description": "Free-text description of standing food preferences, effort tolerance, and cuisine leanings.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_saved_recipes",
            "description": (
                "Search recipes already saved from past suggestions, by title or "
                "cuisine keyword. Prefer reusing a good existing match over "
                "inventing a near-duplicate."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def get_pantry(conn: sqlite3.Connection, exclude_ingredient_ids: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT pantry_item.id AS pantry_item_id, canonical_ingredient.id AS ingredient_id,
               canonical_ingredient.name, canonical_ingredient.category,
               pantry_item.qty_label, pantry_item.is_low
        FROM pantry_item JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id
        ORDER BY canonical_ingredient.name COLLATE NOCASE
        """
    ).fetchall()
    return [
        {
            "pantry_item_id": r["pantry_item_id"],
            "name": r["name"],
            "category": r["category"],
            "note": r["qty_label"],
            "running_low": bool(r["is_low"]),
        }
        for r in rows
        if r["ingredient_id"] not in exclude_ingredient_ids
    ]


def get_recent_meals(conn: sqlite3.Connection, n: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT cook_log.cooked_at, recipe.title, recipe.cuisine
        FROM cook_log JOIN recipe ON recipe.id = cook_log.recipe_id
        ORDER BY cook_log.cooked_at DESC
        LIMIT ?
        """,
        (max(1, n),),
    ).fetchall()
    return [
        {"title": r["title"], "cuisine": r["cuisine"], "cooked_at": r["cooked_at"]} for r in rows
    ]


def get_taste_profile(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT body_text FROM taste_profile WHERE id = 1").fetchone()
    return row["body_text"] if row else ""


def search_saved_recipes(
    conn: sqlite3.Connection, query: str, exclude_ingredient_ids: set[int]
) -> list[dict]:
    like = f"%{query.strip()}%"
    rows = conn.execute(
        """
        SELECT id, title, cuisine, est_minutes, keeps_well
        FROM recipe
        WHERE title LIKE ? ESCAPE '\\' OR cuisine LIKE ? ESCAPE '\\'
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (like, like),
    ).fetchall()

    results = []
    for r in rows:
        ingredient_ids = {
            row["ingredient_id"]
            for row in conn.execute(
                "SELECT ingredient_id FROM recipe_ingredient WHERE recipe_id = ?", (r["id"],)
            )
        }
        if ingredient_ids & exclude_ingredient_ids:
            continue
        names = [
            row["name"]
            for row in conn.execute(
                """
                SELECT canonical_ingredient.name FROM recipe_ingredient
                JOIN canonical_ingredient ON canonical_ingredient.id = recipe_ingredient.ingredient_id
                WHERE recipe_ingredient.recipe_id = ?
                """,
                (r["id"],),
            )
        ]
        results.append(
            {
                "saved_recipe_id": r["id"],
                "title": r["title"],
                "cuisine": r["cuisine"],
                "est_minutes": r["est_minutes"],
                "keeps_well": bool(r["keeps_well"]),
                "ingredients": names,
            }
        )
    return results


def dispatch(conn: sqlite3.Connection, name: str, args: dict, exclude_ingredient_ids: set[int]):
    if name == "get_pantry":
        return get_pantry(conn, exclude_ingredient_ids)
    if name == "get_recent_meals":
        return get_recent_meals(conn, int(args.get("n", 5)))
    if name == "get_taste_profile":
        return get_taste_profile(conn)
    if name == "search_saved_recipes":
        return search_saved_recipes(conn, str(args.get("query", "")), exclude_ingredient_ids)
    return {"error": f"Unknown tool: {name}"}
