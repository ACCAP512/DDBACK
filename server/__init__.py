"""Drawback broker-OS application layer (M0 scaffold).

This package is the multi-tenant application built *around* the pure-stdlib engine
(``engine/drawback/``). The engine is consumed as a library and never modified — see
``docs/BUILD_PLAN.md`` (§1, principle 1) and ``HANDOFF.md``.

Importing ``server`` makes the sibling ``engine/`` directory importable so ``import drawback``
works however the app is launched (uvicorn, alembic, pytest, scripts) — mirroring the path
bootstrap already used by ``api/main.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
if _ENGINE_DIR.is_dir() and str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))
