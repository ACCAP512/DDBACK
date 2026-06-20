"""The commercial<->customs JOIN: import-side reconciliation + export-side proof matching,
including the edge cases (multi-receipt-to-one-entry, qty mismatch, missing customs, no AES)."""

from datetime import date
from decimal import Decimal

from drawback.models import ChargeType, DataQualityReport
from drawback.ingest.customs import AesExportRecord, CustomsEntryLine
from drawback.ingest.records import CommercialExport, CommercialImport
from drawback.ingest import join


def _ci(join_ref, qty, item="X", tranid="IR1", row=2):
    return CommercialImport(
        join_ref=join_ref, item=item, description="commercial desc", quantity=qty,
        unit_of_measure="No.", unit_cost=Decimal("10"), amount=Decimal(str(10 * qty)),
        transaction_date=date(2024, 1, 10), vendor="Vendor", tranid=tranid, source_row=row,
    )


def _ce(entry, qty, join_ref, hts="8501314000", row=2, charges=None, liquidated=True):
    return CustomsEntryLine(
        entry_number=entry, line_number=1, importer_of_record="47-3319008", hts10=hts,
        description="customs desc", import_date=date(2024, 1, 8), entry_date=date(2024, 1, 9),
        quantity=qty, unit_of_measure="No.", entered_value=Decimal(str(10 * qty)),
        charges=charges or {ChargeType.BASE_DUTY: Decimal("100")}, liquidated=liquidated,
        join_ref=join_ref, source_row=row,
    )


# ── IMPORT JOIN ──────────────────────────────────────────────────────────────
def test_import_join_basic_pulls_duty_from_customs_context_from_netsuite():
    rpt = DataQualityReport()
    imports = join.join_imports([_ci("PO-1", 100)], [_ce("ENT-1", 100, "PO-1")], rpt)
    assert len(imports) == 1
    im = imports[0]
    assert im.entry_number == "ENT-1"                 # entry no. from customs
    assert im.importer_id == "47-3319008"             # IOR from customs
    assert im.charges[ChargeType.BASE_DUTY] == Decimal("100")  # duty from customs
    assert im.description == "commercial desc"         # context preferred from NetSuite
    assert im.quantity == 100


def test_multi_receipt_to_one_entry():
    # Two NetSuite receipts (800 + 1200) consolidated under one 7501 line of 2000.
    rpt = DataQualityReport()
    receipts = [_ci("PO-561", 800, tranid="IR-A", row=2), _ci("PO-561", 1200, tranid="IR-B", row=3)]
    customs = [_ce("ENT-561", 2000, "PO-561")]
    imports = join.join_imports(receipts, customs, rpt)
    assert len(imports) == 1                           # ONE designated import (the entry line)
    assert imports[0].quantity == 2000                 # customs qty governs (duty basis)
    assert any("multi-receipt-to-one-entry" in i.message for i in rpt.issues)


def test_quantity_reconciliation_mismatch_flagged():
    rpt = DataQualityReport()
    # commercial 950 vs customs 1000 -> discrepancy reported, customs governs
    imports = join.join_imports([_ci("PO-9", 950)], [_ce("ENT-9", 1000, "PO-9")], rpt)
    assert imports[0].quantity == 1000
    assert any(i.field == "quantity" and "reconciliation" in i.message for i in rpt.issues)


def test_missing_customs_receipt_dropped_and_flagged():
    rpt = DataQualityReport()
    # NetSuite receipt PO-99 has no entry line -> no duty -> dropped (not fabricated)
    imports = join.join_imports([_ci("PO-99", 300, item="CHAIR")], [_ce("ENT-1", 100, "PO-1")], rpt)
    refs = {im.entry_number for im in imports}
    assert refs == {"ENT-1"}                            # PO-99 absent
    assert any("no matching 7501/ACE entry" in i.message for i in rpt.issues)


def test_entry_without_commercial_is_kept_with_customs_context():
    rpt = DataQualityReport()
    imports = join.join_imports([], [_ce("ENT-LONE", 500, "PO-LONE")], rpt)
    assert len(imports) == 1
    assert imports[0].description == "customs desc"     # falls back to 7501 description
    assert any("no matching NetSuite receipt" in i.message for i in rpt.issues)


def test_join_ref_normalization_matches_formatting_variants():
    rpt = DataQualityReport()
    # 'po 561' commercial vs 'PO-561' customs should still join
    imports = join.join_imports([_ci("po 561", 100)], [_ce("ENT-561", 100, "PO-561")], rpt)
    assert len(imports) == 1
    assert not any("no matching" in i.message for i in rpt.issues)


# ── EXPORT JOIN ──────────────────────────────────────────────────────────────
def _cx(join_ref, qty, hint="8501314000", row=2, rate="40"):
    return CommercialExport(
        join_ref=join_ref, item="X", description="sale", quantity=qty, unit_of_measure="No.",
        unit_price=Decimal(rate), amount=Decimal(str(int(float(rate) * qty))),
        transaction_date=date(2025, 3, 1), customer="Cust", ship_country="CA",
        hint_hts=hint, source_row=row,
    )


def _aes(join_ref, qty, hts="8501314000", itn="X2025", bol="BL1", row=2, val="80000"):
    return AesExportRecord(
        itn=itn, hts10=hts, description="exp", export_date=date(2025, 3, 5), quantity=qty,
        unit_of_measure="No.", value_at_export=Decimal(val), destination_country="CA",
        bill_of_lading=bol, join_ref=join_ref, source_row=row,
    )


def test_export_join_with_aes_sets_proof_and_itn():
    rpt = DataQualityReport()
    exports = join.join_exports([_cx("CI-1", 2000)], [_aes("CI-1", 2000)], rpt)
    assert len(exports) == 1
    ex = exports[0]
    assert ex.has_export_proof is True
    assert ex.reference == "X2025"             # ITN becomes the reference (proof token)
    assert ex.proof_kind == "aes_itn"
    assert ex.export_date == date(2025, 3, 5)  # AES date of export is authoritative
    assert ex.hts10 == "8501314000"            # AES Schedule B governs classification


def test_export_join_without_aes_is_unproven_but_classified():
    rpt = DataQualityReport()
    exports = join.join_exports([_cx("CI-NOPROOF", 1500)], [], rpt)
    assert len(exports) == 1
    ex = exports[0]
    assert ex.has_export_proof is False        # no AES -> engine demotes to potential (A-15)
    assert ex.hts10 == "8501314000"            # still classified via NetSuite item HTS hint
    assert any(i.field == "has_export_proof" for i in rpt.issues)


def test_export_join_bill_of_lading_only_is_proof():
    rpt = DataQualityReport()
    exports = join.join_exports([_cx("CI-2", 100)], [_aes("CI-2", 100, itn="")], rpt)
    assert exports[0].has_export_proof is True
    assert exports[0].proof_kind == "bill_of_lading"
    assert exports[0].reference == "BL1"


def test_export_join_aes_without_commercial_is_flagged_unused():
    rpt = DataQualityReport()
    exports = join.join_exports([], [_aes("CI-ORPHAN", 100)], rpt)
    assert exports == []
    assert any("no matching NetSuite sale" in i.message for i in rpt.issues)
