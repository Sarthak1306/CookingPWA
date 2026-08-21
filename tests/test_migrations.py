from app.db import apply_migrations, get_connection


def test_migrations_are_idempotent():
    apply_migrations()
    assert apply_migrations() == []


def test_reapplying_migrations_does_not_touch_existing_data():
    conn = get_connection()
    conn.execute("DELETE FROM user")
    conn.execute("INSERT INTO user (username, password_hash) VALUES ('probe', 'x')")
    conn.commit()
    conn.close()

    apply_migrations()

    conn = get_connection()
    row = conn.execute("SELECT username FROM user WHERE username = 'probe'").fetchone()
    conn.close()
    assert row is not None
