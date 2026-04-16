from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import zenve_db.models  # noqa: F401 — registers all ORM models on Base
from alembic import context

# Import all models so Alembic sees them for autogenerate
from zenve_db.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    from zenve_config.settings import get_settings

    s = get_settings()
    if s.pg_database_url:
        return s.pg_database_url
    return f"sqlite:///{s.sqlite_database_url}"


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
