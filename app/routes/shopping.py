import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db
from app.auth.security import now_iso
from app.ingredients import FALLBACK_COLOR, FALLBACK_EMOJI, pack_label, resolve_ingredient_id

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


class AddShoppingBody(BaseModel):
    ingredient_id: int | None = None
    name: str | None = None
    added_from: str = "recipe"


@router.get("/shopping")
def list_shopping(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        """
        SELECT shopping_item.id, shopping_item.added_at, shopping_item.added_from,
               canonical_ingredient.id AS ingredient_id, canonical_ingredient.name,
               canonical_ingredient.color, canonical_ingredient.emoji
        FROM shopping_item
        JOIN canonical_ingredient ON canonical_ingredient.id = shopping_item.ingredient_id
        ORDER BY canonical_ingredient.name COLLATE NOCASE
        """
    ).fetchall()
    return [
        {
            "id": r["id"],
            "ingredient_id": r["ingredient_id"],
            "name": r["name"],
            "color": r["color"] or FALLBACK_COLOR,
            "emoji": r["emoji"] or FALLBACK_EMOJI,
            "added_from": r["added_from"],
            "added_at": r["added_at"],
        }
        for r in rows
    ]


@router.post("/shopping", status_code=201)
def add_shopping_item(body: AddShoppingBody, conn: sqlite3.Connection = Depends(get_db)):
    """Existence of a shopping_item row means 'still need to buy' — no
    ticked flag (tick-off deletes the row and restocks the pantry instead)
    — so adding twice is a no-op, not a duplicate row. Accepts either a
    known ingredient_id (Recipe detail's "Add missing") or a free-text
    name (the shopping list's own manual-add row), which resolves through
    the same ingredient-identity path the pantry uses, creating a new
    canonical ingredient if it doesn't already exist."""
    if body.ingredient_id is not None:
        ingredient = conn.execute(
            "SELECT id, name FROM canonical_ingredient WHERE id = ?", (body.ingredient_id,)
        ).fetchone()
        if ingredient is None:
            raise HTTPException(status_code=404)
        ingredient_id, name = ingredient["id"], ingredient["name"]
    elif body.name and body.name.strip():
        ingredient_id = resolve_ingredient_id(conn, body.name.strip())
        name = conn.execute(
            "SELECT name FROM canonical_ingredient WHERE id = ?", (ingredient_id,)
        ).fetchone()["name"]
    else:
        raise HTTPException(status_code=400, detail="ingredient_id or name is required")

    existing = conn.execute(
        "SELECT id FROM shopping_item WHERE ingredient_id = ?", (ingredient_id,)
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO shopping_item (ingredient_id, added_from) VALUES (?, ?)",
            (ingredient_id, body.added_from),
        )
        conn.commit()

    return {"ingredient_id": ingredient_id, "name": name, "on_list": True}


@router.post("/shopping/{shopping_item_id}/tick")
def tick_shopping_item(shopping_item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Bought it — leaves the shopping list and lands back in the pantry at
    pack size, mirroring the restock action exactly. Merges into an
    existing pantry_item for that ingredient if one somehow already
    exists, rather than tripping the ingredient_id UNIQUE constraint."""
    row = conn.execute(
        """
        SELECT shopping_item.id, canonical_ingredient.id AS ingredient_id, canonical_ingredient.name,
               canonical_ingredient.common_purchase_qty, canonical_ingredient.common_purchase_unit
        FROM shopping_item
        JOIN canonical_ingredient ON canonical_ingredient.id = shopping_item.ingredient_id
        WHERE shopping_item.id = ?
        """,
        (shopping_item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404)

    conn.execute("DELETE FROM shopping_item WHERE id = ?", (shopping_item_id,))

    pack = pack_label(row) or "restocked"
    existing_pantry_item = conn.execute(
        "SELECT id FROM pantry_item WHERE ingredient_id = ?", (row["ingredient_id"],)
    ).fetchone()
    if existing_pantry_item:
        pantry_item_id = existing_pantry_item["id"]
        conn.execute(
            "UPDATE pantry_item SET qty_label = ?, is_low = 0, updated_at = ? WHERE id = ?",
            (pack, now_iso(), pantry_item_id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO pantry_item (ingredient_id, qty_label, is_low, updated_at) VALUES (?, ?, 0, ?)",
            (row["ingredient_id"], pack, now_iso()),
        )
        pantry_item_id = cur.lastrowid
    conn.commit()

    return {
        "ingredient_id": row["ingredient_id"],
        "name": row["name"],
        "qty_label": pack,
        "pantry_item_id": pantry_item_id,
    }


@router.delete("/shopping/{shopping_item_id}")
def remove_shopping_item(shopping_item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Drops an item from the list without touching the pantry — for a
    mis-add or a change of mind, distinct from tick-off."""
    row = conn.execute("SELECT id FROM shopping_item WHERE id = ?", (shopping_item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    conn.execute("DELETE FROM shopping_item WHERE id = ?", (shopping_item_id,))
    conn.commit()
    return {"ok": True}
