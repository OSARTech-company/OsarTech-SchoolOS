"""Alembic environment script for raw SQL migrations."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger('alembic.env')

# add your model's MetaData object here
# for 'autogenerate' support (we're not using it for raw SQL)
target_metadata = None

def _resolve_database_url() -> str:
    """Resolve DATABASE_URL from environment, .env, or alembic config."""
    env_url = (os.environ.get('DATABASE_URL') or '').strip()
    if env_url:
        return env_url

    # Try loading project .env when running via `python migrate.py`.
    if load_dotenv is not None:
        try:
            project_root = Path(__file__).resolve().parent.parent
            load_dotenv(project_root / '.env', override=False)
        except Exception:
            pass
        env_url = (os.environ.get('DATABASE_URL') or '').strip()
        if env_url:
            return env_url

    cfg_url = (config.get_main_option('sqlalchemy.url') or '').strip()
    if cfg_url:
        return cfg_url
    raise RuntimeError(
        'DATABASE_URL environment variable not set (and no sqlalchemy.url configured).'
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no engine needed)."""
    url = _resolve_database_url()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with engine)."""
    url = _resolve_database_url()

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")
    run_migrations_online()
