"""Customs overlay parsers: 7501/ACE entry summary + AES/EEI export proof, with the
duty-component -> ChargeType mapping (RESEARCH Q14/Q15)."""

from decimal import Decimal

from drawback.models import ChargeType, DataQualityReport
from drawback.ingest import customs


def _rpt():
    return DataQualityReport()


def test_7501_maps_blocks_and_duty_components():
    csv_text = (
        "Entry Number,Entry Date,Import Date,Importer of Record,Country of Origin,Line,HTSUS,"
        "Description,Net Quantity,UOM,Entered Value,Duty,Sec 301,Sec 232,IEEPA,MPF,HMF,"
        "Liquidation Status,PO Number\n"
        "JXM-2310481-7,2023-03-16,2023-03-14,47-3319008,CN,1,8501.31.4000,DC motors,2500,No.,"
        "85000.00,2380.00,21250.00,0.00,0.00,294.44,106.25,LIQUIDATED,PO-10481\n"
    )
    lines = customs.parse_entry_summaries(csv_text, _rpt())
    assert len(lines) == 1
    L = lines[0]
    assert L.entry_number == "JXM-2310481-7"        # blk 1
    assert L.line_number == 1                        # col 31
    assert L.importer_of_record == "47-3319008"      # blk 27
    assert L.hts10 == "8501314000"                   # col 33A normalized to 10 digits
    assert L.import_date.isoformat() == "2023-03-14" # blk 11 -> 5-yr clock
    assert L.quantity == 2500                        # col 35
    assert L.entered_value == Decimal("85000.00")    # col 36A
    assert L.join_ref == "PO-10481"                  # broker join key
    assert L.liquidated is True
    # duty components mapped to the right ChargeType, zero-value fees dropped
    assert L.charges[ChargeType.BASE_DUTY] == Decimal("2380.00")
    assert L.charges[ChargeType.SECTION_301] == Decimal("21250.00")
    assert L.charges[ChargeType.MPF] == Decimal("294.44")     # acct 499
    assert L.charges[ChargeType.HMF] == Decimal("106.25")     # acct 501
    assert ChargeType.SECTION_232 not in L.charges            # 0.00 -> not added


def test_7501_section_232_and_ieepa_split_out():
    csv_text = (
        "Entry Number,Import Date,Line,HTSUS,Net Quantity,UOM,Entered Value,Duty,Sec 301,Sec 232,"
        "IEEPA,MPF,HMF,Liquidation Status,PO Number\n"
        "JXM-2410527-8,2024-04-26,1,7326.90.8635,1600,No.,19200.00,556.80,4800.00,4800.00,0.00,"
        "66.51,24.00,LIQUIDATED,PO-10527\n"
    )
    L = customs.parse_entry_summaries(csv_text, _rpt())[0]
    assert L.charges[ChargeType.SECTION_232] == Decimal("4800.00")   # broker-split 232 -> ineligible bucket
    assert ChargeType.IEEPA not in L.charges


def test_7501_open_liquidation_flag():
    csv_text = (
        "Entry Number,Import Date,Line,HTSUS,Net Quantity,UOM,Entered Value,Duty,MPF,HMF,"
        "Liquidation Status,PO Number\n"
        "JXM-2510702-5,2025-11-22,1,8517.62.0000,700,No.,84700.00,0.00,293.40,105.88,OPEN,PO-10702\n"
    )
    L = customs.parse_entry_summaries(csv_text, _rpt())[0]
    assert L.liquidated is False     # "OPEN" -> not finally liquidated (A-14)


def test_7501_bad_rows_dropped_and_reported():
    csv_text = (
        "Entry Number,Import Date,Line,HTSUS,Net Quantity,UOM,Entered Value,Duty,PO Number\n"
        ",2024-01-01,1,8501.31.4000,10,No.,1000,28,PO-X\n"             # no entry number
        "JXM-1,bad-date,1,8501.31.4000,10,No.,1000,28,PO-Y\n"          # bad date
        "JXM-2,2024-01-01,1,ABC,10,No.,1000,28,PO-Z\n"                 # bad HTS
        "JXM-3,2024-01-01,1,8501.31.4000,10,No.,1000,28,PO-OK\n"       # clean
    )
    rpt = _rpt()
    lines = customs.parse_entry_summaries(csv_text, rpt)
    assert len(lines) == 1
    fields = {i.field for i in rpt.issues if i.severity == "error"}
    assert {"entry_number", "import_date", "hts10"} <= fields


def test_aes_eei_maps_proof_fields():
    csv_text = (
        "ITN,USPPI,Schedule B,Description,Date of Export,Quantity,UOM,Value at Export,"
        "Country of Ultimate Destination,Bill of Lading,Commercial Invoice\n"
        "X20230914000118,47-3319008,8501.31.4000,DC motors,2023-09-14,2000,No.,82000.00,CA,"
        "MAEU2390011842,CI-50012\n"
    )
    recs = customs.parse_aes_eei(csv_text, _rpt())
    assert len(recs) == 1
    a = recs[0]
    assert a.itn == "X20230914000118"               # proof token
    assert a.hts10 == "8501314000"                  # Schedule B normalized
    assert a.export_date.isoformat() == "2023-09-14"
    assert a.quantity == 2000
    assert a.value_at_export == Decimal("82000.00")
    assert a.value_per_unit == Decimal("41")        # derived
    assert a.destination_country == "CA"            # country of ultimate destination
    assert a.bill_of_lading == "MAEU2390011842"
    assert a.join_ref == "CI-50012"                 # commercial-invoice ref -> join key


def test_aes_eei_missing_proof_token_warns_not_drops():
    csv_text = (
        "ITN,Schedule B,Date of Export,Quantity,UOM,Value at Export,Country of Ultimate Destination,"
        "Bill of Lading,Commercial Invoice\n"
        ",8544.42.9000,2025-06-16,4000,No.,20800.00,GB,,CI-50086\n"   # no ITN, no B/L
    )
    rpt = _rpt()
    recs = customs.parse_aes_eei(csv_text, rpt)
    assert len(recs) == 1                            # kept (join still possible; proof flagged missing)
    assert any(i.field == "itn" and i.severity == "warning" for i in rpt.issues)


def test_aes_bill_of_lading_only_is_valid_proof():
    csv_text = (
        "ITN,Schedule B,Date of Export,Quantity,UOM,Value at Export,Country of Ultimate Destination,"
        "Bill of Lading,Commercial Invoice\n"
        ",8544.42.9000,2025-06-16,4000,No.,20800.00,GB,MSCU99,CI-50086\n"  # B/L but no ITN
    )
    rpt = _rpt()
    recs = customs.parse_aes_eei(csv_text, rpt)
    assert recs[0].bill_of_lading == "MSCU99"
    # B/L present -> no missing-proof warning
    assert not any(i.field == "itn" for i in rpt.issues)
