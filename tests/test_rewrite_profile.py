import pytest

import app.llm.openrouter as openrouter_module
from app.db import get_connection, sync_canonical_ingredients
from app.jobs import _process_job


@pytest.fixture(autouse=True, scope="session")
def _seed():
    sync_canonical_ingredients()


@pytest.fixture(autouse=True)
def _clean_slate():
    conn = get_connection()
    conn.execute("DELETE FROM pantry_item")
    conn.execute("DELETE FROM recipe_ingredient")
    conn.execute("DELETE FROM recipe_step")
    conn.execute("DELETE FROM cook_log")
    conn.execute("DELETE FROM recipe")
    conn.execute("DELETE FROM job")
    conn.execute("DELETE FROM llm_call")
    conn.execute(
        "UPDATE taste_profile SET effort = 'An hour is fine', tags_json = '[\"Herby\"]', body_text = 'Original seed text.' WHERE id = 1"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def test_rewrite_profile_job_replaces_body_text_only(auth_client, monkeypatch):
    async def fake_chat_completion(messages, tools=None, model=None):
        return {"role": "assistant", "content": "Rewritten profile prose."}

    monkeypatch.setattr(openrouter_module, "chat_completion", fake_chat_completion)
    import app.llm.rewrite as rewrite_module

    monkeypatch.setattr(rewrite_module, "chat_completion", fake_chat_completion)

    conn = get_connection()
    cur = conn.execute("INSERT INTO job (kind, payload_json, status) VALUES ('rewrite_profile', '{}', 'pending')")
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    import asyncio

    asyncio.run(_process_job(job_id))

    resp = auth_client.get("/api/taste-profile")
    body = resp.json()
    assert body["body_text"] == "Rewritten profile prose."
    assert body["effort"] == "An hour is fine"  # untouched
    assert body["tags"] == ["Herby"]  # untouched

    conn = get_connection()
    job = conn.execute("SELECT status FROM job WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    assert job["status"] == "done"


def test_rewrite_profile_job_error_on_empty_response(auth_client, monkeypatch):
    async def fake_chat_completion(messages, tools=None, model=None):
        return {"role": "assistant", "content": ""}

    import app.llm.rewrite as rewrite_module

    monkeypatch.setattr(rewrite_module, "chat_completion", fake_chat_completion)

    conn = get_connection()
    cur = conn.execute("INSERT INTO job (kind, payload_json, status) VALUES ('rewrite_profile', '{}', 'pending')")
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    import asyncio

    asyncio.run(_process_job(job_id))

    conn = get_connection()
    job = conn.execute("SELECT status, error FROM job WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    assert job["status"] == "error"
    assert job["error"]
