import sqlite3
from pathlib import Path

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_connection() -> sqlite3.Connection:
    # FastAPI dispatches sync dependencies to worker threads and doesn't
    # guarantee a generator dependency's setup and the request handler that
    # consumes it land on the same thread — so a per-request connection has
    # to tolerate that handoff.
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_migrations() -> list[str]:
    """Apply any migration files not yet recorded. Returns the list applied."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migration (
                filename    TEXT PRIMARY KEY,
                applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        conn.commit()

        applied = {row["filename"] for row in conn.execute("SELECT filename FROM schema_migration")}
        pending = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql") if p.name not in applied)

        newly_applied = []
        for filename in pending:
            sql = (MIGRATIONS_DIR / filename).read_text()
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migration (filename) VALUES (?)", (filename,))
            conn.commit()
            newly_applied.append(filename)

        return newly_applied
    finally:
        conn.close()
