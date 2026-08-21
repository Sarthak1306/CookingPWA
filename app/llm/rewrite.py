import sqlite3

from app.config import settings
from app.llm.openrouter import OpenRouterError, chat_completion
from app.llm.spend_guard import record_call

HISTORY_LIMIT = 10

SYSTEM_PROMPT = """You maintain one person's standing taste-profile text for a \
cooking assistant. You'll be given the current profile text and their most \
recent cook history (title, cuisine, rating 1-5 or unrated, when cooked).

Rewrite the profile text to reflect any real pattern in the history — e.g. \
consistently low ratings for a cuisine or style, or a repeated favorite. Keep \
what's still true. Don't overreact to one data point. Keep it to roughly the \
same length as the original (around 150-250 words), plain prose, no headings \
or bullet points.

The one hard rule that must always remain, worded however fits naturally: \
never seafood, beef, or pork.

Respond with ONLY the replacement profile text — no prose about what you \
changed, no markdown, no quotes around it."""


class RewriteError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


async def run_rewrite_profile(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT recipe.title, recipe.cuisine, cook_log.rating, cook_log.cooked_at
        FROM cook_log JOIN recipe ON recipe.id = cook_log.recipe_id
        ORDER BY cook_log.cooked_at DESC
        LIMIT ?
        """,
        (HISTORY_LIMIT,),
    ).fetchall()
    history = "\n".join(
        f"- {r['title']} ({r['cuisine']}), rated "
        f"{r['rating'] if r['rating'] is not None else 'unrated'}, cooked {r['cooked_at']}"
        for r in rows
    )

    current = conn.execute("SELECT body_text FROM taste_profile WHERE id = 1").fetchone()
    current_text = current["body_text"] if current else ""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Current profile text:\n{current_text}\n\nRecent cook history:\n{history or '(none yet)'}",
        },
    ]

    try:
        assistant_msg = await chat_completion(
            messages, model=settings.model_name_cheap or settings.model_name
        )
    except OpenRouterError as exc:
        raise RewriteError("provider_error", str(exc))
    record_call(conn)

    new_text = (assistant_msg.get("content") or "").strip()
    if not new_text:
        raise RewriteError("empty_response", "The model returned an empty profile rewrite.")

    conn.execute(
        "UPDATE taste_profile SET body_text = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = 1",
        (new_text,),
    )
    conn.commit()
    return {"body_text": new_text}
