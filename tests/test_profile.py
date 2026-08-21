import pytest

from app.db import get_connection
from app.llm import tools as tool_impl


@pytest.fixture(autouse=True)
def _reset_profile():
    conn = get_connection()
    conn.execute(
        "UPDATE taste_profile SET effort = '', tags_json = '[]', body_text = 'Seed text.' WHERE id = 1"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def auth_client(client, user):
    client.post("/api/login", json=user)
    return client


def test_get_taste_profile_returns_seeded_row(auth_client):
    resp = auth_client.get("/api/taste-profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["effort"] == ""
    assert body["tags"] == []
    assert body["body_text"] == "Seed text."


def test_patch_taste_profile_updates_only_given_fields(auth_client):
    resp = auth_client.patch(
        "/api/taste-profile", json={"effort": "An hour is fine", "tags": ["Herby", "One-pan"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["effort"] == "An hour is fine"
    assert body["tags"] == ["Herby", "One-pan"]
    assert body["body_text"] == "Seed text."  # untouched

    resp2 = auth_client.patch("/api/taste-profile", json={"body_text": "New words."})
    assert resp2.json()["body_text"] == "New words."
    assert resp2.json()["effort"] == "An hour is fine"  # still untouched


def test_taste_profile_requires_auth(client):
    assert client.get("/api/taste-profile").status_code == 404
    assert client.patch("/api/taste-profile", json={"body_text": "x"}).status_code == 404


def test_get_taste_profile_tool_composes_all_three_fields(auth_client):
    auth_client.patch(
        "/api/taste-profile",
        json={"effort": "Under 20 min", "tags": ["Sharp & lemony"], "body_text": "Loves dal."},
    )
    conn = get_connection()
    composed = tool_impl.get_taste_profile(conn)
    conn.close()
    assert "Under 20 min" in composed
    assert "Sharp & lemony" in composed
    assert "Loves dal." in composed
