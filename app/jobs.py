import asyncio
import json
import logging

from app.db import get_connection
from app.llm.rewrite import RewriteError, run_rewrite_profile
from app.llm.spend_guard import SpendCapExceeded, check_spend_cap
from app.llm.suggest import SuggestError, run_suggest

logger = logging.getLogger("kitchen.jobs")

POLL_INTERVAL_SECONDS = 0.5


async def _process_job(job_id: int) -> None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM job WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return

        conn.execute(
            "UPDATE job SET status = 'running', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (job_id,),
        )
        conn.commit()

        try:
            check_spend_cap(conn)
            payload = json.loads(row["payload_json"])

            if row["kind"] == "suggest":
                result = await run_suggest(
                    conn,
                    payload["query"],
                    payload.get("avoid", []),
                    payload.get("exclude_recipe_ids", []),
                )
            elif row["kind"] == "rewrite_profile":
                result = await run_rewrite_profile(conn)
            else:
                raise SuggestError("unknown_job_kind", f"Unknown job kind: {row['kind']}")

            conn.execute(
                "UPDATE job SET status = 'done', result_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (json.dumps(result), job_id),
            )
        except SpendCapExceeded as exc:
            conn.execute(
                "UPDATE job SET status = 'error', error = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (str(exc), job_id),
            )
        except SuggestError as exc:
            conn.execute(
                "UPDATE job SET status = 'error', error = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (exc.message, job_id),
            )
        except RewriteError as exc:
            conn.execute(
                "UPDATE job SET status = 'error', error = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (exc.message, job_id),
            )
        except Exception as exc:  # noqa: BLE001 — last resort so a job never hangs at "running" forever
            logger.exception("job %s failed", job_id)
            conn.execute(
                "UPDATE job SET status = 'error', error = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                ("Something went wrong. Try again.", job_id),
            )
        conn.commit()
    finally:
        conn.close()


async def worker_loop(stop_event: asyncio.Event) -> None:
    """One in-process worker, serially draining pending jobs. Serial on
    purpose — a single user, and it makes the spend guard trivially
    correct with no concurrent-call races to reason about."""
    while not stop_event.is_set():
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id FROM job WHERE status = 'pending' ORDER BY created_at LIMIT 1"
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            continue

        await _process_job(row["id"])
