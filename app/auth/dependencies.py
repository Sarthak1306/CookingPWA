import sqlite3

from fastapi import Cookie, Depends, HTTPException

from app.auth.security import SESSION_COOKIE_NAME, hash_token, now_iso
from app.db import get_connection


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    conn: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    """Every protected route depends on this. Unauthenticated requests get a
    plain 404 — not 401 — so an unauthenticated caller can't tell the
    difference between a real route and one that doesn't exist."""
    if session is None:
        raise HTTPException(status_code=404)

    row = conn.execute(
        """
        SELECT user.id, user.username, session.id AS session_id
        FROM session JOIN user ON user.id = session.user_id
        WHERE session.token_hash = ?
        """,
        (hash_token(session),),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404)

    conn.execute(
        "UPDATE session SET last_seen_at = ? WHERE id = ?", (now_iso(), row["session_id"])
    )
    conn.commit()

    return row
