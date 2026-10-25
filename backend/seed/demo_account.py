"""Give the seeded SYNTHETIC demo supplier a login (Phase 6; explicit operator action).

    DEMO_ACCOUNT_PASSWORD='choose-a-local-password' make demo-account

Reads DEMO_ACCOUNT_EMAIL (default `demo@paysetu.example`) and DEMO_ACCOUNT_PASSWORD from the
process environment only; the password is never printed or logged. Refuses production.

Email verification (Phase 7A): the demo login starts UNVERIFIED, like every account; verify it
through the development outbox (`make email-outbox`). For automated local runs only,
DEMO_ACCOUNT_VERIFIED=1 marks this one synthetic demo login verified at creation. That is the
only verification shortcut in the code base: it needs an operator command, refuses
production, and applies only to the new login of the unowned synthetic demo supplier.

Only a supplier marked `is_demo` with no owner is ever assigned. Demo data created before
accounts existed therefore stays unowned (unreachable through the API) until this command is
run, and no other supplier row is touched.
"""

import os
import sys

from app.clock import SystemClock
from app.config import AppEnv, load_settings
from app.db import Database
from app.services.auth import create_demo_account

DEFAULT_EMAIL = "demo@paysetu.example"


def main() -> int:
    settings = load_settings()
    if settings.app_env is AppEnv.PRODUCTION:
        print("Refusing to create a demo account in production.", file=sys.stderr)
        return 1
    email = os.environ.get("DEMO_ACCOUNT_EMAIL", DEFAULT_EMAIL)
    password = os.environ.get("DEMO_ACCOUNT_PASSWORD", "")
    verified = os.environ.get("DEMO_ACCOUNT_VERIFIED", "") == "1"
    if not password:
        print("Set DEMO_ACCOUNT_PASSWORD (at least 10 characters).", file=sys.stderr)
        return 1
    database = Database(settings.database_url)
    try:
        with database.session() as session:
            create_demo_account(session, SystemClock(), email, password, verified=verified)
    except ValueError as exc:
        print(f"Demo account not created: {exc}", file=sys.stderr)
        return 1
    finally:
        database.dispose()
    state = "verified (DEMO_ACCOUNT_VERIFIED=1)" if verified else "unverified: sign in to verify"
    print(f"Demo account created for {email}; it owns the synthetic demo supplier; {state}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
