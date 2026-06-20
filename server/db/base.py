"""SQLAlchemy Declarative base, engine factory, and session scope (M0).

A deterministic constraint **naming convention** is set on the metadata so every index / unique /
check / foreign-key / primary-key constraint has a stable name. This is what lets Alembic emit
clean migrations — and, crucially, lets SQLite *batch* ALTERs (table-copy) reconstruct constraints
by name in later milestones without churn.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from server.config import get_database_url

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_engine(url: Optional[str] = None, **kwargs):
    """Build an Engine. Enables SQLite foreign-key enforcement (off by default in SQLite) so the
    referential integrity the schema declares is actually checked in dev."""
    url = url or get_database_url()
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    eng = create_engine(url, future=True, connect_args=connect_args, **kwargs)
    if is_sqlite:
        @event.listens_for(eng, "connect")
        def _enable_sqlite_fk(dbapi_conn, _record):  # pragma: no cover - trivial pragma
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return eng


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session: commit on success, roll back on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
