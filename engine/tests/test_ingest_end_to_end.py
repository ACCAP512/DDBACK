"""End-to-end: ingest the demo NetSuite + customs dirs -> Dataset -> build_estimate,
plus the orchestrator's contract validation (fail-loudly) and the client seam."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from drawback.estimate import build_estimate
from drawback.models import ChargeType, DataQualityReport
from drawback.ingest import (
    IngestionError, StubbedNetSuiteClient, ingest_dataset, ingest_from_client,
)
from drawback.ingest.client import FIXTURE_MODE_BANNER, NetSuiteClient
from drawback.ingest import join as _join
from drawback.ingest.records import CommercialImport
from drawback.ingest.customs import CustomsEntryLine

_REPO = Path(__file__).resolve().parents[2]
_NETSUITE_DIR = _REPO / "samples" / "demo_netsuite"
_CUSTOMS_DIR = _REPO / "samples" / "demo_customs"


def test_demo_dirs_exist():
    assert _NETSUITE_DIR.is_dir() and _CUSTOMS_DIR.is_dir()


def test_ingest_demo_produces_clean_dataset():
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    # no hard schema errors
    errors = [i for i in ds.data_quality.issues if i.severity == "error"]
    assert errors == [], errors
    assert ds.importer_id == "47-3319008"
    assert len(ds.imports) >= 12 and len(ds.exports) >= 10
    # every produced line satisfies the contract the validator enforces
    for im in ds.imports:
        assert len(im.hts10) == 10 and im.quantity > 0 and isinstance(im.entered_value, Decimal)
    for ex in ds.exports:
        assert len(ex.hts10) == 10 and ex.quantity > 0


def test_end_to_end_estimate_has_headline_and_potential():
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    est = build_estimate(ds)
    # non-trivial defensible headline
    assert est.headline_point > Decimal("50000")
    assert est.headline_low > 0
    assert est.headline_low <= est.headline_point <= est.eligible_duty_pool
    # both buckets populated
    assert len(est.headline_pairs()) >= 5
    assert est.potential_total > 0                       # the missing-AES export -> needs review
    # headline reconciles to the by-program breakdown (engine invariant)
    assert sum((b.recovery for b in est.by_program), Decimal("0")) == est.headline_point


def test_end_to_end_exercises_other_basket_and_ineligible_layers():
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    est = build_estimate(ds)
    reasons = est.blocked_by_reason
    # the 7326.90.8688 export is blocked (other-basket, no permissible substitution)
    assert reasons.get("other_basket_no_match", Decimal("0")) > 0
    # the Section-232 steel layers are surfaced as ineligible duty
    assert reasons.get("ineligible_duty_only", Decimal("0")) > 0
    # the missing-AES export shows up as missing-export-proof potential
    assert reasons.get("missing_export_proof", Decimal("0")) > 0
    # the 10-digit "other"-basket substitution (7326.90.8635) made it into the headline
    assert any(b.key == "73269086" for b in est.by_hts)


def test_other_basket_substitution_is_in_headline():
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    est = build_estimate(ds)
    steel_headline = [p for p in est.headline_pairs() if p.hts8 == "73269086"]
    assert steel_headline, "expected the 7326.90.8635 export to substitute at 10-digit into the headline"


def test_out_of_window_import_not_in_headline():
    # PO-10455 imported 2021-02-10 is outside the 5-yr window from AS_OF 2026-06-19.
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    est = build_estimate(ds)
    # no headline pair should reference the pre-window entry
    assert all(p.import_entry != "JXM-2110455-3" for p in est.headline_pairs())


# ── client seam ──────────────────────────────────────────────────────────────
def test_stubbed_client_is_not_connected():
    client = StubbedNetSuiteClient(_NETSUITE_DIR)
    assert client.connected is False
    assert "NOT CONNECTED" in FIXTURE_MODE_BANNER
    assert "NOT CONNECTED" in client.mode
    rpt = DataQualityReport()
    assert len(client.fetch_imports(rpt)) >= 12
    assert len(client.fetch_exports(rpt)) >= 10


def test_ingest_from_client_matches_ingest_dataset():
    a = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    b = ingest_from_client(StubbedNetSuiteClient(_NETSUITE_DIR), _CUSTOMS_DIR)
    assert build_estimate(a).headline_point == build_estimate(b).headline_point


# ── fail-loudly contract validation ──────────────────────────────────────────
def test_invalid_hts_raises_ingestion_error(monkeypatch):
    # Force the join to emit an ImportLine with a non-10-digit HTS -> hard schema break.
    real = _join.join_imports

    def broken(commercial, customs, report):
        lines = real(commercial, customs, report)
        if lines:
            lines[0].hts10 = "8501"            # 4 digits — violates the contract
        return lines

    monkeypatch.setattr(_join, "join_imports", broken)
    with pytest.raises(IngestionError) as exc:
        ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR)
    assert "hts10" in str(exc.value)


def test_strict_false_downgrades_to_report(monkeypatch):
    real = _join.join_imports

    def broken(commercial, customs, report):
        lines = real(commercial, customs, report)
        if lines:
            lines[0].hts10 = "8501"
        return lines

    monkeypatch.setattr(_join, "join_imports", broken)
    ds = ingest_dataset(_NETSUITE_DIR, _CUSTOMS_DIR, strict=False)   # does not raise
    assert any(i.severity == "error" and i.field == "imports" for i in ds.data_quality.issues)
