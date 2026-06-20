"""Background job runner (skeleton, M0).

The MVP plan is a DB-backed job table + this worker polling it (no extra infra). It graduates to a
queue (arq + Valkey — never Redis/SSPL) only if needed. Real jobs (OCR pipelines, report generation)
arrive in M4/M6. For now this is an explicit, importable placeholder so the package layout is locked.
"""
from __future__ import annotations

import server  # noqa: F401  -- path bootstrap


def run_pending_jobs() -> int:
    """Process queued background jobs. No job table exists yet (M4); returns 0 today."""
    return 0


if __name__ == "__main__":  # pragma: no cover
    processed = run_pending_jobs()
    print(f"worker: processed {processed} job(s)")
