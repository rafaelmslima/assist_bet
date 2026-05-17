from __future__ import annotations

import argparse
import getpass

from app.web.user_admin import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a dashboard web user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help=argparse.SUPPRESS)
    parser.add_argument("--role", default="user", choices=["user", "admin"])
    args = parser.parse_args()

    password = getpass.getpass("Password: ") if args.password is None else args.password
    print(create_user(args.email, password, role=args.role))


if __name__ == "__main__":
    main()
