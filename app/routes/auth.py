import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_db
from app.auth.security import (
    LOCKOUT_THRESHOLD,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    hash_token,
    is_locked,
    lockout_expiry,
    new_session_token,
    verify_password,
)
from app.config import settings

router = APIRouter(prefix="/api")


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    user = conn.execute(
        "SELECT id, username, password_hash, failed_attempts, locked_until FROM user WHERE username = ?",
        (body.username,),
    ).fetchone()

    # Same generic error whether the user doesn't exist, the password is
    # wrong, or the account is locked — never reveal which.
    invalid = HTTPException(status_code=401, detail="Invalid username or password")

    if user is None:
        raise invalid

    if is_locked(user["locked_until"]):
        raise invalid

    if not verify_password(body.password, user["password_hash"]):
        attempts = user["failed_attempts"] + 1
        locked_until = lockout_expiry() if attempts >= LOCKOUT_THRESHOLD else None
        conn.execute(
            "UPDATE user SET failed_attempts = ?, locked_until = COALESCE(?, locked_until) WHERE id = ?",
            (attempts, locked_until, user["id"]),
        )
        conn.commit()
        raise invalid

    conn.execute(
        "UPDATE user SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (user["id"],)
    )

    token = new_session_token()
    conn.execute(
        "INSERT INTO session (user_id, token_hash) VALUES (?, ?)",
        (user["id"], hash_token(token)),
    )
    conn.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"username": user["username"]}


@router.post("/logout")
def logout(
    response: Response,
    user: sqlite3.Row = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    conn.execute("DELETE FROM session WHERE id = ?", (user["session_id"],))
    conn.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: sqlite3.Row = Depends(get_current_user)):
    return {"username": user["username"]}
