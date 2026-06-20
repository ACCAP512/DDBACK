"""Minimal FastAPI app for the broker-OS application layer (M0).

Intentionally tiny: it proves the new ``server/`` layer stands up, imports the engine as a library,
and can see its database. The real routers (auth, portfolio, clients, claims, documents) arrive in
M3+. The existing single-claim demo API remains at ``api/main.py`` and is unchanged.

Run:  uvicorn server.api.main:app --port 8001   (from the repo root)
"""
from __future__ import annotations

import server  # noqa: F401  -- path bootstrap: makes `drawback` importable

from fastapi import FastAPI
from sqlalchemy import inspect

from drawback.config import tariff_eligibility as cfg
import server.db.scoping  # noqa: F401  -- registers the tenant-isolation ORM event
from server.api.routers import auth, claims, clients, portfolio
from server.db.base import engine

app = FastAPI(title="Drawback Broker OS", version="0.1.0-m3")

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(claims.router)
app.include_router(portfolio.router)


@app.get("/api/health")
def health() -> dict:
    """Liveness + which dated engine config is loaded."""
    return {
        "ok": True,
        "layer": "server (broker OS)",
        "milestone": "M3",
        "engine_tariff_config": cfg.VERSION,
        "as_of": cfg.AS_OF.isoformat(),
    }


@app.get("/api/readiness")
def readiness() -> dict:
    """Reports whether the schema has been migrated yet (does the DB have our tables?)."""
    table_names = set(inspect(engine).get_table_names())
    migrated = "claims" in table_names and "designations" in table_names
    return {
        "database_reachable": True,
        "schema_migrated": migrated,
        "tables": sorted(table_names),
        "hint": None if migrated else "run `make migrate` (alembic upgrade head)",
    }
