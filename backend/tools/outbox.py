"""Print the newest messages in the development email outbox (Phase 6.1).

    make email-outbox            # list the 10 newest messages, then show the newest one

With EMAIL_MODE=simulated the API writes every email (including password-reset links) to
STORAGE_DIR/outbox/ instead of sending it. This is the controlled, development-only way to
read a reset link: it refuses to run with APP_ENV=production, and it never calls the API.
"""

import sys
from email import message_from_bytes, policy
from pathlib import Path

from app.config import AppEnv, load_settings

SHOW = 10


def main() -> int:
    settings = load_settings()
    if settings.app_env is AppEnv.PRODUCTION:
        print("Refusing to read the email outbox in production.", file=sys.stderr)
        return 1
    folder = Path(settings.storage_dir) / "outbox"
    files = sorted(folder.glob("*.eml")) if folder.exists() else []
    if not files:
        print(f"No messages in {folder}.")
        return 0
    for path in files[-SHOW:]:
        message = message_from_bytes(path.read_bytes(), policy=policy.default)
        print(f"{message['Date']} | {message['X-PaySetu-Kind']} | to {message['To']} | {path.name}")
    newest = message_from_bytes(files[-1].read_bytes(), policy=policy.default)
    print(f"\n--- newest: {newest['Subject']} (to {newest['To']}) ---\n")
    print(newest.get_content())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
