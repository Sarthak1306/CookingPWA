import sqlite3

FALLBACK_CATEGORY = "Other"
FALLBACK_COLOR = "#e6ddc8"
FALLBACK_EMOJI = ""  # a made-up ingredient gets a color, not a guessed icon


def pack_label(row: sqlite3.Row) -> str:
    return f"{row['common_purchase_qty']}{row['common_purchase_unit']}"


def resolve_ingredient_id(conn: sqlite3.Connection, name: str, category: str | None = None) -> int:
    """Case-insensitive match against canonical_ingredient. Creates a new
    row when the name doesn't match anything, so it can still reach the
    shopping list and future LLM matching later — uncategorized unless the
    caller supplies a category (the pantry add/edit screen's optional
    picker). If the ingredient already exists and a category is given,
    that's a user correcting a miscategorized item (e.g. moving something
    out of the "Other" catch-all), so it updates the existing row too.
    Shared by the pantry routes and the LLM suggestion loop's missing[]
    handling — one resolver, one definition of ingredient identity."""
    existing = conn.execute(
        "SELECT id FROM canonical_ingredient WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if existing:
        if category:
            conn.execute(
                "UPDATE canonical_ingredient SET category = ? WHERE id = ?", (category, existing["id"])
            )
        return existing["id"]

    cur = conn.execute(
        """
        INSERT INTO canonical_ingredient
            (name, category, default_unit, deny_flag, common_purchase_qty, common_purchase_unit, color, emoji)
        VALUES (?, ?, '', 0, '', '', ?, ?)
        """,
        (name, category or FALLBACK_CATEGORY, FALLBACK_COLOR, FALLBACK_EMOJI),
    )
    return cur.lastrowid
