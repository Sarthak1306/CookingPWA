"""Create the one Kitchen user. There is no signup endpoint on purpose.

Usage:
    python -m scripts.create_user <username>
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.security import hash_password
from app.db import apply_migrations, get_connection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()

    apply_migrations()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords didn't match.", file=sys.stderr)
        raise SystemExit(1)
    if not password:
        print("Password can't be empty.", file=sys.stderr)
        raise SystemExit(1)

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM user WHERE username = ?", (args.username,)
        ).fetchone()
        if existing:
            print(f"User '{args.username}' already exists.", file=sys.stderr)
            raise SystemExit(1)

        conn.execute(
            "INSERT INTO user (username, password_hash) VALUES (?, ?)",
            (args.username, hash_password(password)),
        )
        conn.commit()
        print(f"Created user '{args.username}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
