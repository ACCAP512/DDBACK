"""Alembic environment for the broker-OS schema.

The DB URL comes from the environment (``DRAWBACK_DATABASE_URL``) via ``server.config`` — or from an
explicit ``sqlalchemy.url`` set on the Config (tests do this) — so secrets are never committed.
``render_as_batch`` is enabled for SQLite so later ALTERs (add column, etc.) work despite SQLite's
limited ALTER support.
"""
from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

import server  # noqa: F401  -- path bootstrap (makes `drawback` importable if needed)
from server.config import get_database_url
from server.db.base import Base
from server.db import models  # noqa: F401  -- import for side effect: register all tables
from server.db.types import Money

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_database_url()


def render_item(type_, obj, autogen_context):
    """Make autogenerate emit our custom ``Money`` type with the import it needs, so generated
    migrations are runnable as written (otherwise ``server.db.types.Money()`` is an undefined name)."""
    if type_ == "type" and isinstance(obj, Money):
        autogen_context.imports.add("import server.db.types")
        return "server.db.types.Money()"
    return False


def run_migrations_offline() -> None:
    url = _url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        render_item=render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _url()
    connectable = create_engine(url, poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
            render_item=render_item,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
