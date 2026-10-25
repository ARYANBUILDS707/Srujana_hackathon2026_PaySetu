"""Plain-text account emails (Phase 6.1). Wording is factual; no legal content."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.mail.senders import OutgoingEmail

IST = ZoneInfo("Asia/Kolkata")


def _ist(instant: datetime) -> str:
    return instant.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def password_reset(to: str, link: str, minutes: int) -> OutgoingEmail:
    body = (
        "Someone asked to reset the password for your PaySetu account.\n\n"
        f"To choose a new password, open this link within {minutes} minutes:\n\n"
        f"{link}\n\n"
        "The link works once. If you did not ask for this, ignore this email: your password "
        "stays the same.\n\n"
        "PaySetu prepares evidence. It is not legal advice.\n"
    )
    return OutgoingEmail(to, "Reset your PaySetu password", body, "password_reset")


def password_changed(to: str, when: datetime, how: str, forgot_link: str) -> OutgoingEmail:
    action = "reset with an emailed link" if how == "reset" else "changed from your account"
    body = (
        f"The password for your PaySetu account was {action} on {_ist(when)}.\n"
        "All other signed-in sessions have been signed out.\n\n"
        "If this was you, no action is needed.\n"
        "If it was not you, reset your password now and check your account:\n\n"
        f"{forgot_link}\n\n"
        "PaySetu prepares evidence. It is not legal advice.\n"
    )
    return OutgoingEmail(to, "Your PaySetu password was changed", body, "password_changed")
