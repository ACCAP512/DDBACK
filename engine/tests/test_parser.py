"""Parser round-trip and data-quality reporting (FR1.2)."""

from decimal import Decimal

from drawback.data.generator import generate, write_csvs
from drawback.data.parser import parse_dataset, parse_imports
from drawback.estimate import build_estimate
from drawback.models import DataQualityReport


def test_csv_round_trip_preserves_estimate(tmp_path):
    ds = generate(seed=42, scale="demo")
    direct = build_estimate(ds)
    imp_path, exp_path = write_csvs(ds, tmp_path)
    reparsed = parse_dataset(imp_path, exp_path)
    from_csv = build_estimate(reparsed)
    assert from_csv.headline_point == direct.headline_point
    assert from_csv.potential_total == direct.potential_total
    assert reparsed.data_quality.imports_dropped == 0
    assert reparsed.data_quality.exports_dropped == 0


def test_data_quality_flags_bad_rows():
    csv_text = (
        "entry_number,line_number,importer_id,hts10,description,import_date,entry_date,quantity,uom,"
        "entered_value,duty_base,duty_301,duty_232,duty_ieepa,mpf,hmf,ad_cvd,excise,country_of_origin,liquidated\n"
        "APX1,1,47-3319008,8501314000,motors,2024-01-15,2024-01-16,10,No.,10000,280,2500,0,0,34.64,12.50,0,0,CN,Y\n"
        "APX2,1,47-3319008,BADHTS,motors,2024-01-15,2024-01-16,10,No.,10000,280,0,0,0,0,0,0,0,CN,Y\n"
        ",1,47-3319008,8501314000,motors,2024-01-15,2024-01-16,10,No.,10000,280,0,0,0,0,0,0,0,CN,Y\n"
        "APX4,1,47-3319008,8501314000,motors,not-a-date,2024-01-16,10,No.,10000,280,0,0,0,0,0,0,0,CN,Y\n"
    )
    report = DataQualityReport()
    imports = parse_imports(csv_text, report)
    assert len(imports) == 1                # only APX1 is clean
    assert report.imports_dropped == 3      # bad HTS, missing entry, bad date
    fields = {iss.field for iss in report.issues if iss.severity == "error"}
    assert {"hts10", "entry_number", "import_date"} <= fields


def test_unknown_hts_is_warning_not_drop():
    csv_text = (
        "entry_number,line_number,importer_id,hts10,description,import_date,entry_date,quantity,uom,"
        "entered_value,duty_base,duty_301,duty_232,duty_ieepa,mpf,hmf,ad_cvd,excise,country_of_origin,liquidated\n"
        "APX1,1,47-3319008,9999999999,widget,2024-01-15,2024-01-16,10,No.,10000,280,0,0,0,0,0,0,0,CN,Y\n"
    )
    report = DataQualityReport()
    imports = parse_imports(csv_text, report)
    assert len(imports) == 1
    assert report.imports_dropped == 0
    assert any(iss.severity == "warning" and iss.field == "hts10" for iss in report.issues)
