"""Demo seed: one SYNTHETIC supplier, one sample buyer and one UNVERIFIED bank rate.

Run with `make seed` (after `make migrate`). Refuses to run when APP_ENV=production.
Idempotent: existing demo rows are left unchanged. Contains no real personal or business data.

Bank rate: the only figure on record is 5.75% from 7 Oct 2026, stated in the LS-03 ideation
document. It is stored with `verified = false`, so every interest figure that uses it is
labelled as using an unverified rate. No earlier rate is inserted because its start date is
not on record; interest periods before 7 Oct 2026 therefore report "rate data unavailable".
"""

import sys
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.clock import SystemClock, format_utc_timestamp
from app.config import AppEnv, load_settings
from app.db import Database
from app.models import BankRate, Buyer, Supplier
from app.repositories import cases as repo

DEMO_SUPPLIER = {
    "legal_name": "Ravi Fasteners (DEMO - synthetic data)",
    "trade_name": "Ravi Fasteners DEMO",
    "udyam_number": "UDYAM-TS-00-0000000",
    "enterprise_class": "micro",
    "major_activity": "manufacturing",
    "udyam_registration_date": date(2024, 6, 12),
    "udyam_verification_status": "self_declared",
    "gstin": None,
    "contact_email": "demo-supplier@example.invalid",
}
DEMO_BUYER = {
    "legal_name": "Apex Auto Components Pvt Ltd (SAMPLE)",
    "contact_name": "Accounts Team (sample)",
    "email": "accounts@example.invalid",
}
UNVERIFIED_RATE = {
    "effective_from": date(2026, 10, 7),
    "rate_bps": 575,
    "source": (
        "LS-03 ideation document (24 Oct 2026), citing rbi.org.in. "
        "NOT verified by PaySetu against an RBI notification."
    ),
}


def seed(session: Session, now: str) -> list[str]:
    created: list[str] = []
    with session.begin():
        supplier = repo.demo_supplier(session)
        if supplier is None:
            supplier = Supplier(
                id=str(uuid.uuid4()), is_demo=True, created_at=now, updated_at=now, **DEMO_SUPPLIER
            )
            session.add(supplier)
            session.flush()
            created.append("demo supplier")
        if not repo.list_buyers(session, supplier.id):
            session.add(
                Buyer(
                    id=str(uuid.uuid4()),
                    supplier_id=supplier.id,
                    gstin=None,
                    created_at=now,
                    updated_at=now,
                    **DEMO_BUYER,
                )
            )
            created.append("sample buyer")
        if not any(
            r.effective_from == UNVERIFIED_RATE["effective_from"]
            for r in repo.list_bank_rates(session)
        ):
            session.add(
                BankRate(
                    id=str(uuid.uuid4()),
                    verified=False,
                    verified_by=None,
                    created_at=now,
                    **UNVERIFIED_RATE,
                )
            )
            created.append("unverified bank rate (5.75% from 2026-10-07)")
    return created


def main() -> int:
    settings = load_settings()
    if settings.app_env is AppEnv.PRODUCTION:
        print("Refusing to seed demo data in production.", file=sys.stderr)
        return 1
    database = Database(settings.database_url)
    try:
        with database.session() as session:
            created = seed(session, format_utc_timestamp(SystemClock().now_utc()))
    finally:
        database.dispose()
    print("Created: " + ", ".join(created) if created else "Demo data already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
