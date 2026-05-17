from __future__ import annotations

import argparse
import getpass

from sqlalchemy.exc import OperationalError

from app.database.repository import create_web_user, get_web_user_by_email, update_web_user_password
from app.database.session import SessionLocal
from app.web.security import hash_password


ADMIN_EMAIL = "rafaelmslima.miranda2@gmail.com"
DEFAULT_USER_ROLE = "user"


def create_user(email: str, password: str, role: str = DEFAULT_USER_ROLE) -> str:
    _validate_password(password)
    normalized_email = email.lower().strip()
    role = _normalize_role(normalized_email, role)
    with SessionLocal() as db:
        try:
            if get_web_user_by_email(db, normalized_email):
                raise SystemExit(f"User already exists: {normalized_email}")
            user = create_web_user(db, email=normalized_email, password_hash=hash_password(password), role=role)
        except OperationalError as exc:
            raise SystemExit(_database_error_message()) from exc
    return f"Created web user {user.email} with role {user.role}."


def change_password(email: str, password: str) -> str:
    _validate_password(password)
    with SessionLocal() as db:
        try:
            user = get_web_user_by_email(db, email)
        except OperationalError as exc:
            raise SystemExit(_database_error_message()) from exc
        if user is None:
            raise SystemExit(f"User not found: {email.lower().strip()}")
        update_web_user_password(db, user, hash_password(password))
    return f"Password changed for {user.email}."


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage dashboard web users.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a web user.")
    create_parser.add_argument("--email", required=True)
    create_parser.add_argument("--role", default=DEFAULT_USER_ROLE, choices=[DEFAULT_USER_ROLE, "admin"])

    password_parser = subparsers.add_parser("password", help="Change a web user's password.")
    password_parser.add_argument("--email", required=True)

    args = parser.parse_args()
    password = _prompt_password()

    if args.command == "create":
        print(create_user(args.email, password, role=args.role))
        return
    if args.command == "password":
        print(change_password(args.email, password))
        return
    raise SystemExit("Unknown command.")


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    return password


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise SystemExit("Password must have at least 8 characters.")


def _normalize_role(email: str, role: str) -> str:
    if role == "admin" and email != ADMIN_EMAIL:
        raise SystemExit(f"Only {ADMIN_EMAIL} can have the admin role.")
    if email == ADMIN_EMAIL:
        return "admin"
    return DEFAULT_USER_ROLE


def _database_error_message() -> str:
    return (
        "Could not read web_users. Check DATABASE_URL and run `alembic upgrade head` "
        "in the target database before managing users."
    )


if __name__ == "__main__":
    main()
