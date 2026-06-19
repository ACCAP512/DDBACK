"""Time-window rules: the 5-year import->claim window and export placement (A-09)."""

from datetime import date

from drawback.rules.time_windows import export_placement_ok, five_year_deadline, within_claim_window


def test_five_year_deadline():
    assert five_year_deadline(date(2024, 1, 15)) == date(2029, 1, 15)
    assert five_year_deadline(date(2020, 2, 29)) == date(2025, 2, 28)  # leap-day fallback


def test_within_claim_window():
    assert within_claim_window(date(2021, 6, 20), date(2026, 6, 19)) is True
    assert within_claim_window(date(2021, 6, 18), date(2026, 6, 19)) is False  # > 5 yrs
    assert within_claim_window(date(2026, 7, 1), date(2026, 6, 19)) is False   # claim before import


def test_export_placement_ordering():
    imp = date(2024, 1, 1)
    claim = date(2026, 1, 1)
    ok, _ = export_placement_ok(imp, date(2024, 6, 1), claim)
    assert ok is True
    ok, reason = export_placement_ok(imp, date(2023, 12, 1), claim)  # export before import
    assert ok is False and "precedes import" in reason
    ok, reason = export_placement_ok(imp, date(2026, 6, 1), claim)   # export after claim
    assert ok is False


def test_export_out_of_5yr_window():
    imp = date(2018, 1, 1)
    ok, reason = export_placement_ok(imp, date(2024, 1, 1), date(2024, 6, 1))
    assert ok is False
    assert "5-year window" in reason
