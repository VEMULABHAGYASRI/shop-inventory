"""Command-line admin tasks.

    python -m app.cli create-user <username>

Used to create the first account (there is no public sign-up page).
"""
import argparse
import getpass
import sys

from pydantic import ValidationError

from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.errors import AppError
from app.schemas.auth import UserCreate
from app.services import auth_service


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="Create a login account")
    create.add_argument("username")
    args = parser.parse_args(argv)

    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    init_db(engine)

    if args.command == "create-user":
        password = getpass.getpass("Password (min 8 characters): ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
        try:
            # Reuse the API's validation rules so the CLI can't create a
            # user the API would have rejected.
            data = UserCreate(username=args.username, password=password)
            with make_session_factory(engine)() as db:
                user = auth_service.create_user(db, data.username, data.password)
        except ValidationError as exc:
            for err in exc.errors():
                print(f"{err['loc'][0]}: {err['msg']}", file=sys.stderr)
            return 1
        except AppError as exc:
            print(exc.message, file=sys.stderr)
            return 1
        print(f"Created user '{user.username}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
