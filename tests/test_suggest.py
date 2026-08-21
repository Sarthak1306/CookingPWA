import json

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
    conn.execute("DELETE FROM recipe")
    conn.execute("DELETE FROM job")
    conn.execute("DELETE FROM llm_call")
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def _script(monkeypatch, turns: list[dict]):
    """Replaces chat_completion with a queue of canned assistant messages."""
    queue = list(turns)

    async def fake_chat_completion(messages, tools=None):
        if not queue:
            raise AssertionError("chat_completion called more times than scripted")
        return queue.pop(0)

    monkeypatch.setattr(openrouter_module, "chat_completion", fake_chat_completion)
    # suggest.py imported chat_completion by name, so patch it there too.
    import app.llm.suggest as suggest_module

    monkeypatch.setattr(suggest_module, "chat_completion", fake_chat_completion)


def _final_message(payload: dict) -> dict:
    return {"role": "assistant", "content": json.dumps(payload)}


def _tool_call_message(name: str, args: dict, call_id: str = "call_1") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
        ],
    }


def test_suggest_creates_and_saves_a_recipe(auth_client, monkeypatch):
    chicken = auth_client.post("/api/pantry", json={"name": "Chicken thighs"}).json()

    _script(
        monkeypatch,
        [
            _tool_call_message("get_pantry", {}),
            _final_message(
                {
                    "results": [
                        {
                            "source": "new",
                            "saved_recipe_id": None,
                            "title": "Test Chicken Bake",
                            "cuisine": "Test",
                            "est_minutes": 20,
                            "keeps_well": False,
                            "base_servings": 2,
                            "have_pantry_item_ids": [chicken["id"]],
                            "missing": [{"name": "Test Sauce", "qty": "1", "unit": "jar"}],
                            "steps": [{"text": "Do it", "timer_seconds": None}],
                        }
                    ]
                }
            ),
        ],
    )

    job = auth_client.post("/api/suggest", json={"query": "chicken"}).json()
    assert job["job_id"]

    import asyncio

    asyncio.run(_process_job(job["job_id"]))

    status = auth_client.get(f"/api/jobs/{job['job_id']}").json()
    assert status["status"] == "done"
    assert len(status["recipes"]) == 1
    assert status["recipes"][0]["title"] == "Test Chicken Bake"
    assert status["recipes"][0]["have_count"] == 1
    assert status["recipes"][0]["missing_count"] == 1

    recipe_id = status["recipes"][0]["id"]
    detail = auth_client.get(f"/api/recipes/{recipe_id}").json()
    names_have = {i["name"]: i["have"] for i in detail["ingredients"]}
    assert names_have["Chicken thighs"] is True
    assert names_have["Test Sauce"] is False


def test_suggest_rejects_denied_ingredient_after_retry(auth_client, monkeypatch):
    violating = _final_message(
        {
            "results": [
                {
                    "source": "new",
                    "title": "Test Salmon Thing",
                    "cuisine": "Test",
                    "est_minutes": 10,
                    "keeps_well": False,
                    "base_servings": 2,
                    "have_pantry_item_ids": [],
                    "missing": [{"name": "Salmon fillets", "qty": "1", "unit": ""}],
                    "steps": [],
                }
            ]
        }
    )
    _script(monkeypatch, [violating, violating])

    job = auth_client.post("/api/suggest", json={"query": "fish"}).json()

    import asyncio

    asyncio.run(_process_job(job["job_id"]))

    status = auth_client.get(f"/api/jobs/{job['job_id']}").json()
    assert status["status"] == "error"
    assert "salmon" in status["error"].lower()


def test_avoid_chip_excludes_pantry_item_from_tool_result(auth_client, monkeypatch):
    onions = auth_client.post("/api/pantry", json={"name": "Onions"}).json()
    auth_client.post("/api/pantry", json={"name": "Rice"})

    seen_pantry_names = []

    async def fake_chat_completion(messages, tools=None):
        # First call: trigger a get_pantry tool call.
        if len(messages) == 2:
            return _tool_call_message("get_pantry", {})
        # Second call: messages now include the tool result — inspect it.
        tool_msg = next(m for m in messages if m.get("role") == "tool")
        pantry = json.loads(tool_msg["content"])
        seen_pantry_names.extend(p["name"] for p in pantry)
        return _final_message({"results": []})

    monkeypatch.setattr(openrouter_module, "chat_completion", fake_chat_completion)
    import app.llm.suggest as suggest_module

    monkeypatch.setattr(suggest_module, "chat_completion", fake_chat_completion)

    job = auth_client.post("/api/suggest", json={"query": "anything", "avoid": ["Onions"]}).json()

    import asyncio

    asyncio.run(_process_job(job["job_id"]))

    assert "Onions" not in seen_pantry_names
    assert "Rice" in seen_pantry_names
    assert onions["id"]  # sanity: fixture actually created the row
