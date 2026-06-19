"""The assumption registry must cover every assumption id the traces actually reference (glass-box
source-of-truth), with valid tags, and expose exactly the user-correctable one (A-21)."""

import re

from drawback.assumptions import REGISTRY, Tag, get, registry_summary
from drawback.data.generator import generate
from drawback.estimate import build_estimate

_ID = re.compile(r"\bA-\d{2}\b")


def test_every_traced_assumption_is_registered():
    est = build_estimate(generate(scale="demo"))
    referenced = set()
    for p in est.matched_pairs:
        for a in p.trace.assumption_ids:
            m = _ID.search(a)
            if m:
                referenced.add(m.group(0))
    assert referenced, "demo estimate should reference some assumptions"
    missing = {a for a in referenced if a not in REGISTRY}
    assert not missing, f"trace references assumptions absent from the registry: {sorted(missing)}"


def test_tags_are_valid():
    for a in REGISTRY.values():
        assert isinstance(a.tag, Tag)


def test_a21_is_the_correctable_one():
    correctable = [a.id for a in REGISTRY.values() if a.correctable]
    assert correctable == ["A-21"], f"expected only A-21 correctable, got {correctable}"
    a21 = REGISTRY["A-21"]
    assert a21.correction is not None
    assert "Section 301" in a21.correction.confirm_label or "301" in a21.correction.confirm_label


def test_get_accepts_trace_strings():
    assert get("A-21 (comparator rate profile)").id == "A-21"
    assert get("A-03").id == "A-03"
    assert get("nonsense") is None


def test_registry_summary_shape():
    s = registry_summary()
    assert s["count"] == len(REGISTRY)
    a21 = next(r for r in s["assumptions"] if r["id"] == "A-21")
    assert a21["correctable"] is True and "correction" in a21
