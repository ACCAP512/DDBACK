"""Test fixtures for the server layer: an isolated SQLite database per test.

Each test gets a fresh file-backed SQLite DB (built via ``Base.metadata.create_all``), so tests never
touch the dev DB and never see each other's rows.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from server.db import models  # noqa: F401  -- register all tables on Base.metadata
from server.db.base import Base, make_engine


@pytest.fixture()
def engine(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def session(engine) -> Session:
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    s = factory()
    try:
        yield s
    finally:
        s.close()
