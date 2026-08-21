import json
import sqlite3

from app.ingredients import resolve_ingredient_id
from app.llm import tools as tool_impl
from app.llm.dedup import find_duplicate_recipe
from app.llm.deny_list import find_deny_violations
from app.llm.openrouter import OpenRouterError, chat_completion
from app.llm.spend_guard import record_call

MAX_TOOL_ROUNDS = 6
MAX_JSON_RETRIES = 2
MAX_DENY_RETRIES = 1

SYSTEM_PROMPT = """You are a cooking assistant helping one person decide what to cook.

Hard rule, enforced in code as well as here: NEVER suggest a recipe containing \
seafood, beef, or pork, in any form, ever. This is not a preference, it is an \
absolute constraint.

The pantry tracks identity only — whether an ingredient is owned, not how much. \
Never reason about quantities on hand or imply precise stock levels.

Use the tools available to gather context (pantry contents, recent meals, taste \
profile, saved recipes matching a theme) before answering. Prefer reusing a good \
saved recipe over inventing a near-duplicate.

When you are done gathering context, respond with ONLY a single JSON object \
(no prose, no markdown fences) matching exactly this shape:

{
  "results": [
    {
      "source": "new" | "saved",
      "saved_recipe_id": <int, required if source is "saved", else null>,
      "title": <string>,
      "cuisine": <string>,
      "est_minutes": <int>,
      "keeps_well": <bool>,
      "base_servings": <int, typically 2>,
      "have_pantry_item_ids": [<pantry_item_id from get_pantry, int, ...>],
      "missing": [{"name": <string>, "qty": <string>, "unit": <string>}],
      "steps": [{"text": <string>, "timer_seconds": <int or null>}]
    }
  ]
}

For "source": "saved" results, have_pantry_item_ids/missing/steps are ignored — \
just return the saved_recipe_id, title, cuisine, est_minutes, keeps_well, and \
base_servings. Return 2 to 5 results, ranked best first."""


class SuggestError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _exclude_ingredient_ids(conn: sqlite3.Connection, names: list[str]) -> set[int]:
    ids = set()
    for name in names:
        row = conn.execute(
            "SELECT id FROM canonical_ingredient WHERE lower(name) = lower(?)", (name.strip(),)
        ).fetchone()
        if row:
            ids.add(row["id"])
    return ids


async def _run_loop(conn: sqlite3.Connection, messages: list[dict], exclude_ids: set[int]) -> dict:
    json_retries = 0
    for _ in range(MAX_TOOL_ROUNDS):
        try:
            assistant_msg = await chat_completion(messages, tools=tool_impl.TOOL_SCHEMAS)
        except OpenRouterError as exc:
            raise SuggestError("provider_error", str(exc))
        record_call(conn)
        messages.append(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls")
        if tool_calls:
            for call in tool_calls:
                fn = call["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tool_impl.dispatch(conn, fn["name"], args, exclude_ids)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result),
                    }
                )
            continue

        content = (assistant_msg.get("content") or "").strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            json_retries += 1
            if json_retries > MAX_JSON_RETRIES:
                raise SuggestError("malformed_json", "The model didn't return valid JSON after retries.")
            messages.append(
                {
                    "role": "user",
                    "content": "That wasn't valid JSON matching the schema. Respond with ONLY the JSON object, nothing else.",
                }
            )
            continue

        if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
            raise SuggestError("malformed_json", "The model's JSON didn't match the expected shape.")
        return parsed

    raise SuggestError("too_many_iterations", "The model didn't finish after several tool calls.")


def _ingredient_names_in_result(conn: sqlite3.Connection, result: dict) -> list[str]:
    names = [m.get("name", "") for m in result.get("missing", [])]
    ids = result.get("have_pantry_item_ids", [])
    if ids:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""
            SELECT canonical_ingredient.name FROM pantry_item
            JOIN canonical_ingredient ON canonical_ingredient.id = pantry_item.ingredient_id
            WHERE pantry_item.id IN ({placeholders})
            """,
            ids,
        ).fetchall()
        names += [r["name"] for r in rows]
    return names


def _pantry_item_ids_to_ingredient_ids(conn: sqlite3.Connection, pantry_item_ids: list[int]) -> list[int]:
    if not pantry_item_ids:
        return []
    placeholders = ",".join("?" * len(pantry_item_ids))
    rows = conn.execute(
        f"SELECT ingredient_id FROM pantry_item WHERE id IN ({placeholders})", pantry_item_ids
    ).fetchall()
    return [r["ingredient_id"] for r in rows]


def _save_new_recipe(conn: sqlite3.Connection, result: dict) -> int:
    missing_ids = [resolve_ingredient_id(conn, m["name"]) for m in result.get("missing", [])]
    have_ids = _pantry_item_ids_to_ingredient_ids(conn, result.get("have_pantry_item_ids", []))

    all_ids = set(have_ids) | set(missing_ids)
    dup_id = find_duplicate_recipe(conn, result["title"], all_ids)
    if dup_id is not None:
        return dup_id

    cur = conn.execute(
        """
        INSERT INTO recipe (title, base_servings, source, cuisine, est_minutes, keeps_well)
        VALUES (?, ?, 'llm', ?, ?, ?)
        """,
        (
            result["title"],
            result.get("base_servings", 2),
            result.get("cuisine", ""),
            result.get("est_minutes"),
            bool(result.get("keeps_well", False)),
        ),
    )
    recipe_id = cur.lastrowid

    for ing_id in have_ids:
        conn.execute(
            "INSERT OR IGNORE INTO recipe_ingredient (recipe_id, ingredient_id, qty, unit, optional_flag) VALUES (?, ?, '', '', 0)",
            (recipe_id, ing_id),
        )
    for m, ing_id in zip(result.get("missing", []), missing_ids):
        conn.execute(
            "INSERT OR IGNORE INTO recipe_ingredient (recipe_id, ingredient_id, qty, unit, optional_flag) VALUES (?, ?, ?, ?, 0)",
            (recipe_id, ing_id, m.get("qty", ""), m.get("unit", "")),
        )
    for i, step in enumerate(result.get("steps", [])):
        conn.execute(
            "INSERT INTO recipe_step (recipe_id, position, text, timer_seconds) VALUES (?, ?, ?, ?)",
            (recipe_id, i, step.get("text", ""), step.get("timer_seconds")),
        )
    conn.commit()
    return recipe_id


async def run_suggest(conn: sqlite3.Connection, query: str, avoid: list[str]) -> dict:
    exclude_ids = _exclude_ingredient_ids(conn, avoid)
    avoid_note = f" Avoid: {', '.join(avoid)}." if avoid else ""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{query.strip() or 'Something good for tonight.'}{avoid_note}"},
    ]

    parsed = await _run_loop(conn, messages, exclude_ids)

    for attempt in range(MAX_DENY_RETRIES + 1):
        violations: set[str] = set()
        for result in parsed["results"]:
            names = _ingredient_names_in_result(conn, result)
            violations.update(find_deny_violations(names))
        if not violations:
            break
        if attempt == MAX_DENY_RETRIES:
            raise SuggestError(
                "dietary_violation",
                f"Kept suggesting a denied ingredient ({', '.join(sorted(violations))}) after a retry.",
            )
        messages.append(
            {
                "role": "user",
                "content": (
                    f"That included {', '.join(sorted(violations))}, which violates the hard "
                    "no-seafood/beef/pork rule. Regenerate without it, same JSON shape only."
                ),
            }
        )
        parsed = await _run_loop(conn, messages, exclude_ids)

    recipe_ids: list[int] = []
    for result in parsed["results"]:
        if result.get("source") == "saved" and result.get("saved_recipe_id"):
            row = conn.execute(
                "SELECT id FROM recipe WHERE id = ?", (result["saved_recipe_id"],)
            ).fetchone()
            if row:
                recipe_ids.append(row["id"])
                continue
        recipe_ids.append(_save_new_recipe(conn, result))

    return {"recipe_ids": recipe_ids}
