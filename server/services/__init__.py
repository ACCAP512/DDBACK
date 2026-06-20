"""Service layer — the seam between the pure-stdlib engine and the persistence layer.

Translates DB rows ↔ engine dataclasses and runs the engine's public pipeline
(``ingest → build_estimate → harden``) server-side. The engine is never imported *into* the DB and
the DB is never imported *into* the engine — the dependency only ever points one way (app → engine),
preserving the moat and the engine's 112-test suite (BUILD_PLAN §1).
"""
