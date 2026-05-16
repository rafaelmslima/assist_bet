from __future__ import annotations

import argparse
import getpass

from app.database.repository import create_web_user, get_web_user_by_email
from app.database.session import SessionLocal, init_db
from app.web.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a dashboard web user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password")
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Password must have at least 8 characters.")

    init_db()
    with SessionLocal() as db:
        if get_web_user_by_email(db, args.email):
            raise SystemExit(f"User already exists: {args.email.lower().strip()}")
        user = create_web_user(
            db,
            email=args.email,
            password_hash=hash_password(password),
            role=args.role,
        )
    print(f"Created web user {user.email} with role {user.role}.")


if __name__ == "__main__":
    main()
