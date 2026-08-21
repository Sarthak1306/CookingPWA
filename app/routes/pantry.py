import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db
from app.auth.security import now_iso
from app.ingredients import (
    FALLBACK_COLOR,
    FALLBACK_EMOJI,
    pack_label,
    resolve_ingredient_id,
)

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


def _pantry_item_out(conn: sqlite3.Connection, pantry_item_id: int) -> dict:
    row = conn.execute(
        """
        SELECT pantry_item.id, pantry_item.qty_label, pantry_item.is_low, pantry_item.updated_at,
               canonical_ingredient.id AS ingredient_id, canonical_ingredient.name,
               canonical_ingredient.category, canonical_ingredient.common_purchase_qty,
               canonical_ingredient.common_purchase_unit, canonical_ingredient.color,
               canonical_ingredient.emoji
        FROM pantry_item JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id
        WHERE pantry_item.id = ?
        """,
        (pantry_item_id,),
    ).fetchone()
    return {
        "id": row["id"],
        "ingredient_id": row["ingredient_id"],
        "name": row["name"],
        "category": row["category"],
        "qty_label": row["qty_label"],
        "is_low": bool(row["is_low"]),
        "pack": pack_label(row),
        "color": row["color"] or FALLBACK_COLOR,
        "emoji": row["emoji"] or FALLBACK_EMOJI,
        "updated_at": row["updated_at"],
    }


def _upsert_pantry_item(
    conn: sqlite3.Connection,
    name: str,
    qty_label: str,
    is_low: bool,
    editing_pantry_item_id: int | None,
) -> int:
    """Shared by add and edit. Resolves `name` to a canonical ingredient
    (creating one if it's new), then writes exactly one pantry_item for
    that ingredient — merging into an existing row rather than ever
    tripping the ingredient_id UNIQUE constraint, since low friction beats
    a form that can reject you for typing an existing item's name."""
    ingredient_id = resolve_ingredient_id(conn, name)

    if editing_pantry_item_id is not None:
        current = conn.execute(
            "SELECT ingredient_id FROM pantry_item WHERE id = ?", (editing_pantry_item_id,)
        ).fetchone()
        if current is None:
            raise HTTPException(status_code=404)
        if current["ingredient_id"] != ingredient_id:
            # Renamed to a different ingredient's name — drop this row and
            # merge into that ingredient's pantry row instead.
            conn.execute("DELETE FROM pantry_item WHERE id = ?", (editing_pantry_item_id,))

    target = conn.execute(
        "SELECT id FROM pantry_item WHERE ingredient_id = ?", (ingredient_id,)
    ).fetchone()

    if target:
        conn.execute(
            "UPDATE pantry_item SET qty_label = ?, is_low = ?, updated_at = ? WHERE id = ?",
            (qty_label, is_low, now_iso(), target["id"]),
        )
        return target["id"]

    cur = conn.execute(
        "INSERT INTO pantry_item (ingredient_id, qty_label, is_low, updated_at) VALUES (?, ?, ?, ?)",
        (ingredient_id, qty_label, is_low, now_iso()),
    )
    return cur.lastrowid


class AddItemBody(BaseModel):
    name: str
    qty_label: str = ""
    is_low: bool = False


class EditItemBody(BaseModel):
    name: str
    qty_label: str = ""
    is_low: bool = False


@router.get("/pantry")
def list_pantry(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        """
        SELECT pantry_item.id, pantry_item.qty_label, pantry_item.is_low, pantry_item.updated_at,
               canonical_ingredient.id AS ingredient_id, canonical_ingredient.name,
               canonical_ingredient.category, canonical_ingredient.common_purchase_qty,
               canonical_ingredient.common_purchase_unit, canonical_ingredient.color,
               canonical_ingredient.emoji
        FROM pantry_item JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id
        ORDER BY canonical_ingredient.name COLLATE NOCASE
        """
    ).fetchall()
    return [
        {
            "id": r["id"],
            "ingredient_id": r["ingredient_id"],
            "name": r["name"],
            "category": r["category"],
            "qty_label": r["qty_label"],
            "is_low": bool(r["is_low"]),
            "pack": pack_label(r),
            "color": r["color"] or FALLBACK_COLOR,
            "emoji": r["emoji"] or FALLBACK_EMOJI,
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


@router.get("/ingredients")
def search_ingredients(q: str = "", conn: sqlite3.Connection = Depends(get_db)):
    q = q.strip()
    if not q:
        return []
    rows = conn.execute(
        """
        SELECT id, name, category, common_purchase_qty, common_purchase_unit, color, emoji
        FROM canonical_ingredient
        WHERE name LIKE ? ESCAPE '\\'
        ORDER BY name COLLATE NOCASE
        LIMIT 8
        """,
        ("%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "pack": pack_label(r),
            "color": r["color"] or FALLBACK_COLOR,
            "emoji": r["emoji"] or FALLBACK_EMOJI,
        }
        for r in rows
    ]


@router.post("/pantry", status_code=201)
def add_pantry_item(body: AddItemBody, conn: sqlite3.Connection = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ingredient name is required")

    item_id = _upsert_pantry_item(conn, name, body.qty_label.strip(), body.is_low, None)
    conn.commit()
    return _pantry_item_out(conn, item_id)


@router.patch("/pantry/{pantry_item_id}")
def edit_pantry_item(
    pantry_item_id: int, body: EditItemBody, conn: sqlite3.Connection = Depends(get_db)
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ingredient name is required")

    item_id = _upsert_pantry_item(conn, name, body.qty_label.strip(), body.is_low, pantry_item_id)
    conn.commit()
    return _pantry_item_out(conn, item_id)


@router.post("/pantry/{pantry_item_id}/restock")
def restock_pantry_item(pantry_item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        """
        SELECT pantry_item.id, canonical_ingredient.common_purchase_qty, canonical_ingredient.common_purchase_unit
        FROM pantry_item JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id
        WHERE pantry_item.id = ?
        """,
        (pantry_item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404)

    pack = pack_label(row) or "restocked"
    conn.execute(
        "UPDATE pantry_item SET qty_label = ?, is_low = 0, updated_at = ? WHERE id = ?",
        (pack, now_iso(), pantry_item_id),
    )
    conn.commit()
    return _pantry_item_out(conn, pantry_item_id)


@router.post("/pantry/{pantry_item_id}/out-of-stock")
def mark_out_of_stock(pantry_item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """The Suggest screen's one-tap 'out of stock' exclusion — per spec this
    writes to the pantry and persists, i.e. it's gone, not just avoided for
    one request. No shopping-list write here; that's the cook-flow's
    ran-out checklist (P3) and manual adds (P6), both out of scope."""
    row = conn.execute("SELECT id FROM pantry_item WHERE id = ?", (pantry_item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    conn.execute("DELETE FROM pantry_item WHERE id = ?", (pantry_item_id,))
    conn.commit()
    return {"ok": True}
