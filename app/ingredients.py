import sqlite3

FALLBACK_CATEGORY = "Other"
FALLBACK_COLOR = "#e6ddc8"
FALLBACK_EMOJI = ""  # a made-up ingredient gets a color, not a guessed icon


def pack_label(row: sqlite3.Row) -> str:
    return f"{row['common_purchase_qty']}{row['common_purchase_unit']}"


def resolve_ingredient_id(conn: sqlite3.Connection, name: str) -> int:
    """Case-insensitive match against canonical_ingredient. Creates a new
    row — uncategorized — when the name doesn't match anything, so it can
    still reach the shopping list and future LLM matching later. Shared by
    the pantry routes and the LLM suggestion loop's missing[] handling —
    one resolver, one definition of ingredient identity."""
    existing = conn.execute(
        "SELECT id FROM canonical_ingredient WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if existing:
        return existing["id"]

    cur = conn.execute(
        """
        INSERT INTO canonical_ingredient
            (name, category, default_unit, deny_flag, common_purchase_qty, common_purchase_unit, color, emoji)
        VALUES (?, ?, '', 0, '', '', ?, ?)
        """,
        (name, FALLBACK_CATEGORY, FALLBACK_COLOR, FALLBACK_EMOJI),
    )
    return cur.lastrowid
