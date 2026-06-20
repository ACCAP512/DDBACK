"""M0 gate: ``alembic upgrade head`` builds the full domain schema on a clean database.

A regression test for the migration itself — distinct from ``create_all`` (which the other tests use)
because the migration is what actually runs in dev/prod.
"""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from server.config import REPO_ROOT

EXPECTED_TABLES = {
    "tenants", "users", "clients", "programs", "claims",
    "import_entry_lines", "export_lines", "designations",
    "documents", "checklist_items", "tasks", "audit_events",
}


def test_alembic_upgrade_head_builds_schema(tmp_path, monkeypatch):
    db = tmp_path / "migrated.db"
    url = f"sqlite:///{db}"
    monkeypatch.setenv("DRAWBACK_DATABASE_URL", url)

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "server" / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")

    tables = set(inspect(create_engine(url)).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"migration did not create: {sorted(missing)}"
    assert "alembic_version" in tables
