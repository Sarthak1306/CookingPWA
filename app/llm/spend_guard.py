import sqlite3
from datetime import datetime, timezone

from app.config import settings


class SpendCapExceeded(Exception):
    pass


def calls_this_month(conn: sqlite3.Connection) -> int:
    start_of_month = datetime.now(timezone.utc).strftime("%Y-%m-01T00:00:00.000000Z")
    (count,) = conn.execute(
        "SELECT COUNT(*) FROM llm_call WHERE created_at >= ?", (start_of_month,)
    ).fetchone()
    return count


def check_spend_cap(conn: sqlite3.Connection) -> None:
    if calls_this_month(conn) >= settings.monthly_call_cap:
        raise SpendCapExceeded(
            f"Monthly LLM call cap ({settings.monthly_call_cap}) reached. Try again next month."
        )


def record_call(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO llm_call DEFAULT VALUES")
    conn.commit()
