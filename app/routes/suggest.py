import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db
from app.ingredients import FALLBACK_COLOR, FALLBACK_EMOJI
from app.llm.spend_guard import SpendCapExceeded, check_spend_cap

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])

REWRITE_EVERY_N_COOKS = 10


class SuggestBody(BaseModel):
    query: str = ""
    avoid: list[str] = []


class RateBody(BaseModel):
    rating: int


@router.post("/suggest", status_code=202)
def create_suggest_job(body: SuggestBody, conn: sqlite3.Connection = Depends(get_db)):
    try:
        check_spend_cap(conn)
    except SpendCapExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    payload = json.dumps({"query": body.query, "avoid": body.avoid})
    cur = conn.execute(
        "INSERT INTO job (kind, payload_json, status) VALUES ('suggest', ?, 'pending')",
        (payload,),
    )
    conn.commit()
    return {"job_id": cur.lastrowid}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT * FROM job WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404)

    result = json.loads(row["result_json"]) if row["result_json"] else None
    recipes = None
    if result and result.get("recipe_ids"):
        recipes = [_recipe_summary(conn, rid) for rid in result["recipe_ids"]]

    return {
        "id": row["id"],
        "status": row["status"],
        "error": row["error"],
        "recipes": recipes,
    }


def _recipe_summary(conn: sqlite3.Connection, recipe_id: int) -> dict:
    recipe = conn.execute("SELECT * FROM recipe WHERE id = ?", (recipe_id,)).fetchone()
    counts = conn.execute(
        """
        SELECT
          SUM(CASE WHEN pantry_item.id IS NOT NULL THEN 1 ELSE 0 END) AS have_count,
          SUM(CASE WHEN pantry_item.id IS NULL THEN 1 ELSE 0 END) AS missing_count
        FROM recipe_ingredient
        LEFT JOIN pantry_item ON pantry_item.ingredient_id = recipe_ingredient.ingredient_id
        WHERE recipe_ingredient.recipe_id = ?
        """,
        (recipe_id,),
    ).fetchone()
    return {
        "id": recipe["id"],
        "title": recipe["title"],
        "cuisine": recipe["cuisine"],
        "est_minutes": recipe["est_minutes"],
        "keeps_well": bool(recipe["keeps_well"]),
        "difficulty": recipe["difficulty"],
        "have_count": counts["have_count"] or 0,
        "missing_count": counts["missing_count"] or 0,
    }


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, servings: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    recipe = conn.execute("SELECT * FROM recipe WHERE id = ?", (recipe_id,)).fetchone()
    if recipe is None:
        raise HTTPException(status_code=404)

    ingredient_rows = conn.execute(
        """
        SELECT canonical_ingredient.id AS ingredient_id, canonical_ingredient.name,
               canonical_ingredient.color, canonical_ingredient.emoji,
               recipe_ingredient.qty, recipe_ingredient.unit, recipe_ingredient.optional_flag,
               pantry_item.id AS pantry_item_id, shopping_item.id AS shopping_item_id
        FROM recipe_ingredient
        JOIN canonical_ingredient ON canonical_ingredient.id = recipe_ingredient.ingredient_id
        LEFT JOIN pantry_item ON pantry_item.ingredient_id = recipe_ingredient.ingredient_id
        LEFT JOIN shopping_item ON shopping_item.ingredient_id = recipe_ingredient.ingredient_id
        WHERE recipe_ingredient.recipe_id = ?
        ORDER BY canonical_ingredient.name COLLATE NOCASE
        """,
        (recipe_id,),
    ).fetchall()

    steps = conn.execute(
        "SELECT position, text, timer_seconds FROM recipe_step WHERE recipe_id = ? ORDER BY position",
        (recipe_id,),
    ).fetchall()

    return {
        "id": recipe["id"],
        "title": recipe["title"],
        "cuisine": recipe["cuisine"],
        "est_minutes": recipe["est_minutes"],
        "keeps_well": bool(recipe["keeps_well"]),
        "difficulty": recipe["difficulty"],
        "base_servings": recipe["base_servings"],
        "servings": servings or recipe["base_servings"],
        "ingredients": [
            {
                "ingredient_id": r["ingredient_id"],
                "name": r["name"],
                "color": r["color"] or FALLBACK_COLOR,
                "emoji": r["emoji"] or FALLBACK_EMOJI,
                "qty": r["qty"],
                "unit": r["unit"],
                "optional": bool(r["optional_flag"]),
                "have": r["pantry_item_id"] is not None,
                "pantry_item_id": r["pantry_item_id"],
                "on_shopping_list": r["shopping_item_id"] is not None,
            }
            for r in ingredient_rows
        ],
        "steps": [
            {"position": s["position"], "text": s["text"], "timer_seconds": s["timer_seconds"]}
            for s in steps
        ],
    }


@router.post("/recipes/{recipe_id}/cook", status_code=201)
def cook_recipe(recipe_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Marks a recipe cooked — step-by-step cook mode is P4, so for now
    this just logs it (closing the loop for get_recent_meals) and hands
    back the pantry items it used, for the ran-out checklist. Rating and
    notes aren't collected yet; no screen asks for them."""
    recipe = conn.execute("SELECT id FROM recipe WHERE id = ?", (recipe_id,)).fetchone()
    if recipe is None:
        raise HTTPException(status_code=404)

    cur = conn.execute("INSERT INTO cook_log (recipe_id) VALUES (?)", (recipe_id,))
    conn.commit()

    (total_cooks,) = conn.execute("SELECT COUNT(*) FROM cook_log").fetchone()
    if total_cooks % REWRITE_EVERY_N_COOKS == 0:
        conn.execute("INSERT INTO job (kind, payload_json, status) VALUES ('rewrite_profile', '{}', 'pending')")
        conn.commit()

    used = conn.execute(
        """
        SELECT pantry_item.id AS pantry_item_id, canonical_ingredient.name
        FROM recipe_ingredient
        JOIN canonical_ingredient ON canonical_ingredient.id = recipe_ingredient.ingredient_id
        JOIN pantry_item ON pantry_item.ingredient_id = recipe_ingredient.ingredient_id
        WHERE recipe_ingredient.recipe_id = ?
        ORDER BY canonical_ingredient.name COLLATE NOCASE
        """,
        (recipe_id,),
    ).fetchall()

    return {
        "cook_log_id": cur.lastrowid,
        "recipe_id": recipe_id,
        "used_pantry_items": [
            {"pantry_item_id": r["pantry_item_id"], "name": r["name"]} for r in used
        ],
    }


@router.post("/cook-log/{cook_log_id}/rate")
def rate_cook_log(cook_log_id: int, body: RateBody, conn: sqlite3.Connection = Depends(get_db)):
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5.")
    row = conn.execute("SELECT id FROM cook_log WHERE id = ?", (cook_log_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    conn.execute("UPDATE cook_log SET rating = ? WHERE id = ?", (body.rating, cook_log_id))
    conn.commit()
    return {"ok": True}
