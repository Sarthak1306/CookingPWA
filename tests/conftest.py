import os
import tempfile

import pytest

# app.config.settings is a module-level singleton read at import time, so
# the env vars have to be set before anything under app/ is imported.
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["KITCHEN_DB_PATH"] = _db_file.name
os.environ["KITCHEN_COOKIE_SECURE"] = "0"

from app.auth.security import hash_password  # noqa: E402
from app.db import apply_migrations, get_connection  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _migrate():
    apply_migrations()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user():
    conn = get_connection()
    conn.execute("DELETE FROM session")
    conn.execute("DELETE FROM user")
    conn.execute(
        "INSERT INTO user (username, password_hash) VALUES (?, ?)",
        ("sam", hash_password("correcthorse")),
    )
    conn.commit()
    conn.close()
    return {"username": "sam", "password": "correcthorse"}
