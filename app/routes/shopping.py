import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


class AddShoppingBody(BaseModel):
    ingredient_id: int
    added_from: str = "recipe"


@router.post("/shopping", status_code=201)
def add_shopping_item(body: AddShoppingBody, conn: sqlite3.Connection = Depends(get_db)):
    """Existence of a shopping_item row means 'still need to buy' — no
    ticked flag (P6 deletes the row on tick-off) — so adding twice is a
    no-op, not a duplicate row."""
    ingredient = conn.execute(
        "SELECT id, name FROM canonical_ingredient WHERE id = ?", (body.ingredient_id,)
    ).fetchone()
    if ingredient is None:
        raise HTTPException(status_code=404)

    existing = conn.execute(
        "SELECT id FROM shopping_item WHERE ingredient_id = ?", (body.ingredient_id,)
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO shopping_item (ingredient_id, added_from) VALUES (?, ?)",
            (body.ingredient_id, body.added_from),
        )
        conn.commit()

    return {"ingredient_id": ingredient["id"], "name": ingredient["name"], "on_list": True}
