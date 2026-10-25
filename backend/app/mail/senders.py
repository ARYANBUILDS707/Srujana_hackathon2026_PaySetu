"""Email senders (ARCHITECTURE.md 10; Phase 6.1).

- `EMAIL_MODE=simulated`: `FileOutboxSender` writes each message as an `.eml` file to
  `STORAGE_DIR/outbox/` (directory 0700, files 0600). This is the local email sink and the
  only development-time way to read a reset link. With `APP_ENV=production` (allowed only with
  ALLOW_NONLIVE_VERIFIED=1) the body is withheld, so no usable reset link is ever written to
  disk on a production host.
- `EMAIL_MODE=smtp`: `SmtpSender` uses SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD /
  SMTP_STARTTLS / EMAIL_FROM from the environment. 15 s timeout, no automatic retry (API.md 6).

`deliver` never raises: it returns whether the provider accepted the message and logs only
the kind, outcome, mode and user ID, never the address, body, link or token.
"""

import logging
import os
import smtplib
import ssl
import time
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Protocol

from app.clock import Clock
from app.config import AppEnv, EmailMode, Settings
from app.logging import LOGGER_NAME

SMTP_TIMEOUT_SECONDS = 15
DEFAULT_FROM = "PaySetu <no-reply@paysetu.invalid>"
WITHHELD_BODY = (
    "[Body withheld: EMAIL_MODE=simulated on a production server. Configure SMTP to deliver "
    "this message.]\n"
)

logger = logging.getLogger(f"{LOGGER_NAME}.mail")


class EmailDeliveryError(Exception):
    """The message was not accepted for delivery. The message text is safe to log."""


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str
    kind: str  # e.g. "password_reset", "password_changed"


class EmailSender(Protocol):
    mode: str

    def send(self, message: OutgoingEmail) -> None:
        """Hand the message to the provider, or raise `EmailDeliveryError`."""
        ...


def _mime(message: OutgoingEmail, sender: str) -> EmailMessage:
    mime = EmailMessage()
    mime["From"] = sender
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime["Date"] = formatdate(localtime=False)
    mime["Message-ID"] = make_msgid(domain="paysetu.invalid")
    mime["X-PaySetu-Kind"] = message.kind
    mime.set_content(message.body)
    return mime


class FileOutboxSender:
    mode = "simulated"

    def __init__(self, directory: Path, sender: str, clock: Clock, *, withhold_body: bool) -> None:
        self.directory = directory
        self.sender = sender
        self.clock = clock
        self.withhold_body = withhold_body

    def send(self, message: OutgoingEmail) -> None:
        if self.withhold_body:
            message = OutgoingEmail(message.to, message.subject, WITHHELD_BODY, message.kind)
        stamp = self.clock.now_utc().strftime("%Y%m%dT%H%M%S%fZ")
        # time_ns keeps files in send order even when the injected clock is frozen (tests).
        name = f"{stamp}-{time.time_ns()}-{message.kind}-{uuid.uuid4().hex[:8]}.eml"
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            temp = self.directory / f".{name}.tmp"
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(_mime(message, self.sender).as_bytes())
            temp.replace(self.directory / name)
        except OSError as exc:
            raise EmailDeliveryError(f"outbox write failed ({type(exc).__name__})") from None


class SmtpSender:
    mode = "smtp"

    def __init__(self, settings: Settings) -> None:
        assert settings.smtp_host and settings.email_from  # guaranteed by Settings validation
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.starttls = settings.smtp_starttls
        self.sender = settings.email_from

    def send(self, message: OutgoingEmail) -> None:
        try:
            with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
                if self.starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if self.username and self.password:
                    smtp.login(self.username, self.password.get_secret_value())
                smtp.send_message(_mime(message, self.sender))
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(f"SMTP delivery failed ({type(exc).__name__})") from None


def build_sender(settings: Settings, clock: Clock) -> EmailSender:
    if settings.email_mode is EmailMode.SMTP:
        return SmtpSender(settings)
    return FileOutboxSender(
        Path(settings.storage_dir) / "outbox",
        settings.email_from or DEFAULT_FROM,
        clock,
        withhold_body=settings.app_env is AppEnv.PRODUCTION,
    )


def deliver(sender: EmailSender, message: OutgoingEmail, user_id: str) -> bool:
    """Send; log the outcome without personal data or secrets; True only if accepted."""
    try:
        sender.send(message)
    except EmailDeliveryError as exc:
        logger.warning(
            "email delivery failed: %s",
            exc,
            extra={
                "event": "email_delivery",
                "kind": message.kind,
                "outcome": "failed",
                "mode": sender.mode,
                "user_id": user_id,
            },
        )
        return False
    logger.info(
        "email accepted for delivery",
        extra={
            "event": "email_delivery",
            "kind": message.kind,
            "outcome": "sent",
            "mode": sender.mode,
            "user_id": user_id,
        },
    )
    return True
