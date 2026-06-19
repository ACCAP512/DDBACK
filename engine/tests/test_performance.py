"""Performance (FR1.7). Concrete target: a realistic mid-market dataset estimates in a few seconds.

The per-8-digit-HTS bucket decomposition is the scale strategy; realistic HTS diversity keeps each
MCMF subproblem small. See LIMITATIONS.md for the pathological single-HTS mega-bucket seam.
"""

import time

from drawback.data.generator import generate
from drawback.estimate import build_estimate


def test_medium_dataset_under_budget():
    ds = generate(seed=42, scale="medium")  # ~1,500 import lines + exports
    n = len(ds.imports) + len(ds.exports)
    t = time.time()
    est = build_estimate(ds)
    dt = time.time() - t
    assert est.headline_point >= 0
    assert dt < 5.0, f"estimate on {n} lines took {dt:.2f}s (budget 5s)"


def test_large_dataset_completes():
    ds = generate(seed=7, scale="large")    # ~4,000 import lines + exports, ~50 HTS subheadings
    n = len(ds.imports) + len(ds.exports)
    t = time.time()
    est = build_estimate(ds)
    dt = time.time() - t
    assert est.headline_point >= 0
    # generous ceiling; documents the realistic scale point. Per-bucket MCMF cost grows with bucket
    # density; real-world HTS diversity (hundreds of subheadings) keeps buckets smaller than this set.
    assert dt < 30.0, f"estimate on {n} lines took {dt:.2f}s"
