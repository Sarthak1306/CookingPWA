import json
import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


class TasteProfilePatch(BaseModel):
    effort: str | None = None
    tags: list[str] | None = None
    body_text: str | None = None


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "effort": row["effort"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "body_text": row["body_text"],
        "updated_at": row["updated_at"],
    }


@router.get("/taste-profile")
def get_taste_profile_route(conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT effort, tags_json, body_text, updated_at FROM taste_profile WHERE id = 1"
    ).fetchone()
    return _row_to_dict(row)


@router.patch("/taste-profile")
def patch_taste_profile(body: TasteProfilePatch, conn: sqlite3.Connection = Depends(get_db)):
    """Only the effort/tags/body_text buttons the user actually touched are
    sent — the periodic rewrite job (app/llm/rewrite.py) only ever writes
    body_text directly via SQL, never through this route, so it can't
    silently move a button the user didn't press."""
    updates: dict = {}
    if body.effort is not None:
        updates["effort"] = body.effort
    if body.tags is not None:
        updates["tags_json"] = json.dumps(body.tags)
    if body.body_text is not None:
        updates["body_text"] = body.body_text

    if updates:
        set_clause = ", ".join(f"{col} = ?" for col in updates)
        conn.execute(
            f"UPDATE taste_profile SET {set_clause}, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = 1",
            list(updates.values()),
        )
        conn.commit()

    row = conn.execute(
        "SELECT effort, tags_json, body_text, updated_at FROM taste_profile WHERE id = 1"
    ).fetchone()
    return _row_to_dict(row)
