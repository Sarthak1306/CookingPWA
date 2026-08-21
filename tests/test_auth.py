def test_unauthenticated_protected_route_returns_404_not_401(client):
    resp = client.get("/api/me")
    assert resp.status_code == 404


def test_login_wrong_password_returns_401(client, user):
    resp = client.post("/api/login", json={"username": "sam", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(client, user):
    resp = client.post("/api/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_login_then_me_succeeds(client, user):
    resp = client.post("/api/login", json={"username": "sam", "password": "correcthorse"})
    assert resp.status_code == 200
    assert resp.json() == {"username": "sam"}

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == {"username": "sam"}


def test_logout_revokes_session(client, user):
    client.post("/api/login", json={"username": "sam", "password": "correcthorse"})
    assert client.get("/api/me").status_code == 200

    client.post("/api/logout")
    assert client.get("/api/me").status_code == 404


def test_five_failed_attempts_locks_the_account(client, user):
    for _ in range(5):
        resp = client.post("/api/login", json={"username": "sam", "password": "wrong"})
        assert resp.status_code == 401

    # Correct password no longer works while locked.
    resp = client.post("/api/login", json={"username": "sam", "password": "correcthorse"})
    assert resp.status_code == 401
