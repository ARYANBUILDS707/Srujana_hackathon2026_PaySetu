"""Provision PaySetu reviewers (Phase 7C). The only way to grant the reviewer role.

    make reviewer ARGS='create --email reviewer@example.com --name "A Reviewer"'
    make reviewer ARGS='grant --email someone@example.com'
    make reviewer ARGS='revoke --email reviewer@example.com'
    make reviewer ARGS='list'

`create` makes a reviewer-only staff account (no supplier workspace). The password is typed
twice at a hidden prompt, or read from standard input with `--password-stdin` (for scripted
setups); it is never an argument, never printed and never logged. `--operator` records who
issued the grant (default: the OS user name). Requires direct database access (DATABASE_URL),
which is the trust boundary: no HTTP route can grant the role.
"""

import argparse
import getpass
import sys
from collections.abc import Sequence

from app.clock import SystemClock
from app.config import load_settings
from app.db import Database
from app.services import reviewers


def _password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Password for the new reviewer: ")
    if getpass.getpass("Repeat the password: ") != first:
        raise ValueError("The passwords do not match.")
    return first


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.reviewer", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a reviewer-only staff account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--password-stdin", action="store_true")
    for name, help_text in (
        ("grant", "give an existing account the reviewer role"),
        ("revoke", "revoke a reviewer grant"),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--email", required=True)
    for sub in (create, commands.choices["grant"], commands.choices["revoke"]):
        sub.add_argument("--operator", default=getpass.getuser())
    commands.add_parser("list", help="list reviewer grants, including revoked ones")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    database = Database(load_settings().database_url)
    clock = SystemClock()
    try:
        with database.session() as session:
            if args.command == "create":
                reviewers.create_reviewer(
                    session,
                    clock,
                    email=args.email,
                    full_name=args.name,
                    password=_password(args.password_stdin),
                    operator=args.operator,
                )
                print(f"Reviewer account created for {args.email.strip().lower()}.")
            elif args.command == "grant":
                reviewers.grant_reviewer(session, clock, email=args.email, operator=args.operator)
                print(f"Reviewer role granted to {args.email.strip().lower()}.")
            elif args.command == "revoke":
                reviewers.revoke_reviewer(session, clock, email=args.email, operator=args.operator)
                print(f"Reviewer role revoked for {args.email.strip().lower()}.")
            else:
                for row in reviewers.list_reviewers(session):
                    state = f"revoked {row.revoked_at}" if row.revoked_at else "active"
                    kind = "also a supplier" if row.owns_supplier else "staff only"
                    print(
                        f"{row.email}\t{row.full_name}\t{state}\t"
                        f"granted {row.granted_at} by {row.granted_by}\t{kind}"
                    )
    except ValueError as exc:
        print(f"Not done: {exc}", file=sys.stderr)
        return 1
    finally:
        database.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
