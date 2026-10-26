"""postgresql append only

Revision ID: 6b0d2f4a8c31
Revises: 3d7a9c1e5b20
Create Date: 2026-10-26 12:00:00.000000+00:00

Hand-reviewed (hosted deployment on PostgreSQL / Supabase). No-op on SQLite, which already has
these rules as triggers from earlier migrations. On PostgreSQL it creates the equivalents
(DATABASE.md Section 6), so append-only data stays append-only on the hosted database:

- No UPDATE, DELETE or TRUNCATE: `timeline_events`, `business_submissions`,
  `business_certificates`, `business_reviews`, `business_checks`, `business_check_items`.
- `evidence_items`: no DELETE or TRUNCATE; an UPDATE may only set `excluded_at` and
  `excluded_reason`, once (same rule as the SQLite `evidence_items_exclusion_only` trigger).
- `udyam_claims`: no DELETE or TRUNCATE; only `contested` may change.
- `reviewer_grants`: no DELETE or TRUNCATE; only `revoked_at`/`revoked_by` may change, once.
- The "only a demo supplier may be unowned" rule is already a CHECK on PostgreSQL (099b88746350).

Supabase hardening: Supabase serves tables in the public schema through its REST API to the
`anon` and `authenticated` roles. PaySetu never uses that API (the backend connects as the
table owner), so row-level security is enabled on every table with no policies, and those
roles' privileges are revoked when they exist. The owner bypasses RLS, so the app is unchanged.
No row is read or changed.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b0d2f4a8c31"
down_revision: str | Sequence[str] | None = "3d7a9c1e5b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMMUTABLE = (
    "timeline_events",
    "business_submissions",
    "business_certificates",
    "business_reviews",
    "business_checks",
    "business_check_items",
)
NO_DELETE = ("evidence_items", "udyam_claims", "reviewer_grants")
GUARDED_UPDATES = {
    "evidence_items": "paysetu_evidence_exclusion_only",
    "udyam_claims": "paysetu_claim_contested_only",
    "reviewer_grants": "paysetu_grant_revoke_only",
}

FUNCTIONS = {
    "paysetu_append_only": """
        CREATE FUNCTION paysetu_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only: %', TG_TABLE_NAME;
        END $$""",
    # The same rule as the SQLite trigger: only the exclusion fields change, from NULL, once.
    "paysetu_evidence_exclusion_only": """
        CREATE FUNCTION paysetu_evidence_exclusion_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.excluded_at IS NOT NULL
               OR NEW.excluded_at IS NULL OR NEW.excluded_reason IS NULL
               OR (to_jsonb(NEW) - 'excluded_at' - 'excluded_reason')
                  IS DISTINCT FROM (to_jsonb(OLD) - 'excluded_at' - 'excluded_reason') THEN
                RAISE EXCEPTION 'append-only: evidence_items (exclusion only)';
            END IF;
            RETURN NEW;
        END $$""",
    "paysetu_claim_contested_only": """
        CREATE FUNCTION paysetu_claim_contested_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (to_jsonb(NEW) - 'contested') IS DISTINCT FROM (to_jsonb(OLD) - 'contested') THEN
                RAISE EXCEPTION 'udyam_claims may only change contested';
            END IF;
            RETURN NEW;
        END $$""",
    "paysetu_grant_revoke_only": """
        CREATE FUNCTION paysetu_grant_revoke_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.revoked_at IS NOT NULL
               OR (to_jsonb(NEW) - 'revoked_at' - 'revoked_by')
                  IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at' - 'revoked_by') THEN
                RAISE EXCEPTION 'reviewer_grants may only be revoked, once';
            END IF;
            RETURN NEW;
        END $$""",
}

# Every table PaySetu creates, plus Alembic's version table.
ALL_TABLES = (
    "alembic_version",
    "users",
    "sessions",
    "password_reset_tokens",
    "email_verification_tokens",
    "suppliers",
    "buyers",
    "cases",
    "evidence_items",
    "timeline_events",
    "buyer_responses",
    "bank_rates",
    "business_certificates",
    "business_profiles",
    "business_submissions",
    "udyam_claims",
    "reviewer_grants",
    "business_checks",
    "business_check_items",
    "business_reviews",
)
SUPABASE_API_ROLES = ("anon", "authenticated")


def _triggers() -> list[tuple[str, str, str]]:
    """(trigger name, table, CREATE statement) for every PostgreSQL trigger."""
    out = []
    for table in IMMUTABLE:
        out.append(
            (
                f"{table}_no_change",
                table,
                f"CREATE TRIGGER {table}_no_change BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION paysetu_append_only()",
            )
        )
    for table in NO_DELETE:
        out.append(
            (
                f"{table}_no_delete",
                table,
                f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION paysetu_append_only()",
            )
        )
        out.append(
            (
                f"{table}_guarded_update",
                table,
                f"CREATE TRIGGER {table}_guarded_update BEFORE UPDATE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {GUARDED_UPDATES[table]}()",
            )
        )
    for table in (*IMMUTABLE, *NO_DELETE):  # row triggers do not see TRUNCATE
        out.append(
            (
                f"{table}_no_truncate",
                table,
                f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
                "FOR EACH STATEMENT EXECUTE FUNCTION paysetu_append_only()",
            )
        )
    return out


def _roles_exist() -> str:
    names = ", ".join(f"'{r}'" for r in SUPABASE_API_ROLES)
    return f"(SELECT count(*) FROM pg_roles WHERE rolname IN ({names})) = {len(SUPABASE_API_ROLES)}"


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
    for statement in FUNCTIONS.values():
        op.execute(statement)
    for _, _, statement in _triggers():
        op.execute(statement)
    for table in ALL_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    roles = ", ".join(SUPABASE_API_ROLES)
    op.execute(
        f"DO $$ BEGIN IF {_roles_exist()} THEN "
        f"EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {roles}'; "
        f"EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {roles}'; "
        "END IF; END $$"
    )


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
    for table in ALL_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for name, table, _ in reversed(_triggers()):
        op.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}")
    for name in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {name}()")
