"""Alembic environment for PaySetu (T1.2; DATABASE.md Section 8).

Database URL, in order of precedence:
1. `config.attributes["database_url"]` (set programmatically, e.g. by the test fixture);
2. `DATABASE_URL` from validated application settings (`app.config.load_settings`).

Online migrations use `app.db.create_db_engine`, so SQLite migrations run with the same
pragmas as the application (foreign keys, WAL, busy timeout).
"""

from logging.config import fileConfig

from alembic import context

from app.config import load_settings
from app.db import create_db_engine, is_sqlite_url
from app.models import Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    override = config.attributes.get("database_url")
    if isinstance(override, str) and override:
        return override
    return load_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (`alembic upgrade head --sql`)."""
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite_url(url),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    engine = create_db_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # SQLite cannot ALTER most constraints; batch mode rebuilds tables instead.
                render_as_batch=is_sqlite_url(url),
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
