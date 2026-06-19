"""JSON serialization for the API and sample outputs (stdlib only).

Money Decimals -> floats rounded to cents (display side); the canonical Decimal computation stays
server-side. Dates -> ISO strings; enums -> their value. Traces are emitted in full so the glass-box
UI can render every claimed dollar's basis.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from drawback.models import Estimate, MatchedPair


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(round(obj, 2))
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, date):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {(k.value if isinstance(k, Enum) else str(k)): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def estimate_to_dict(est: Estimate, *, include_pairs: bool = True, max_pairs: int = 5000) -> dict:
    """Full Estimate payload for the API. ``include_pairs`` can be turned off for a light summary."""
    d = to_jsonable(est)
    # Add convenience summary fields the UI leads with.
    d["summary"] = {
        "headline_point": float(round(est.headline_point, 2)),
        "headline_low": float(round(est.headline_low, 2)),
        "potential_total": float(round(est.potential_total, 2)),
        "eligible_duty_pool": float(round(est.eligible_duty_pool, 2)),
        "headline_pair_count": len(est.headline_pairs()),
        "total_pair_count": len(est.matched_pairs),
        "imports": est.data_quality.imports_parsed,
        "exports": est.data_quality.exports_parsed,
    }
    if not include_pairs:
        d["matched_pairs"] = []
    elif len(est.matched_pairs) > max_pairs:
        d["matched_pairs"] = to_jsonable(est.matched_pairs[:max_pairs])
        d["matched_pairs_truncated"] = len(est.matched_pairs) - max_pairs
    return d


def pair_to_dict(pair: MatchedPair) -> dict:
    return to_jsonable(pair)
