import sqlite3
from difflib import SequenceMatcher

TITLE_SIMILARITY_THRESHOLD = 0.82
INGREDIENT_OVERLAP_THRESHOLD = 0.6


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_duplicate_recipe(
    conn: sqlite3.Connection, title: str, ingredient_ids: set[int]
) -> int | None:
    """Near-duplicate title plus overlapping ingredient set means show the
    existing recipe instead of saving a sixth variation of the same dal."""
    if not ingredient_ids:
        return None
    for row in conn.execute("SELECT id, title FROM recipe"):
        if _title_similarity(title, row["title"]) < TITLE_SIMILARITY_THRESHOLD:
            continue
        existing_ids = {
            r["ingredient_id"]
            for r in conn.execute(
                "SELECT ingredient_id FROM recipe_ingredient WHERE recipe_id = ?", (row["id"],)
            )
        }
        if not existing_ids:
            continue
        overlap = len(ingredient_ids & existing_ids) / len(ingredient_ids | existing_ids)
        if overlap >= INGREDIENT_OVERLAP_THRESHOLD:
            return row["id"]
    return None
