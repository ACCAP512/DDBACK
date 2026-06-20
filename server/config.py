"""Server configuration (M0).

Settings come from the environment so nothing secret is committed (guardrail: no hardcoded
secrets). Dev defaults to a local SQLite file; prod sets ``DRAWBACK_DATABASE_URL`` to Postgres
via the pg8000 driver, e.g. ``postgresql+pg8000://user:pass@host/dbname``.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / "samples"

_DEFAULT_SQLITE = REPO_ROOT / "drawback_dev.db"


def get_database_url() -> str:
    """Resolve the DB URL fresh from the environment on every call, so tests and Alembic can
    override it via ``DRAWBACK_DATABASE_URL`` without import-order surprises."""
    return os.environ.get("DRAWBACK_DATABASE_URL", f"sqlite:///{_DEFAULT_SQLITE}")


# Convenience snapshot for the common app path; tooling that needs override-ability calls
# get_database_url() directly.
DATABASE_URL = get_database_url()
