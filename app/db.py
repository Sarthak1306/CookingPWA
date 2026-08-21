import json
import sqlite3
from pathlib import Path

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


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


def sync_canonical_ingredients() -> int:
    """Keep the starter fixture's own rows up to date on every startup —
    an upsert by name, not a one-time seed. Editing the curated color,
    emoji, pack size, etc. in fixtures/canonical_ingredients.json and
    restarting is how those changes reach an existing database. Only rows
    matching a fixture name are touched, so ingredients created by hand or
    by the LLM (later phases) are never written to, and pantry_item is
    never touched at all."""
    conn = get_connection()
    try:
        fixture_path = FIXTURES_DIR / "canonical_ingredients.json"
        items = json.loads(fixture_path.read_text())
        cur = conn.executemany(
            """
            UPDATE canonical_ingredient
            SET default_unit = :default_unit, category = :category, deny_flag = :deny_flag,
                common_purchase_qty = :common_purchase_qty, common_purchase_unit = :common_purchase_unit,
                color = :color, emoji = :emoji
            WHERE lower(name) = lower(:name)
            """,
            items,
        )
        updated = cur.rowcount

        existing = {
            row["name"].lower()
            for row in conn.execute("SELECT name FROM canonical_ingredient")
        }
        new_items = [i for i in items if i["name"].lower() not in existing]
        if new_items:
            conn.executemany(
                """
                INSERT INTO canonical_ingredient
                    (name, default_unit, category, deny_flag, common_purchase_qty, common_purchase_unit, color, emoji)
                VALUES (:name, :default_unit, :category, :deny_flag, :common_purchase_qty, :common_purchase_unit, :color, :emoji)
                """,
                new_items,
            )
        conn.commit()
        return len(new_items) + (updated if updated > 0 else 0)
    finally:
        conn.close()
