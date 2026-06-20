"""NetSuite spine parsers (JSON + CSV) — real field names -> intermediate commercial records."""

from decimal import Decimal

from drawback.models import DataQualityReport
from drawback.ingest import netsuite


def _rpt():
    return DataQualityReport()


def test_import_spine_csv_maps_real_fields():
    csv_text = (
        "Internal ID,Type,Document Number,Date,Name,Other Ref Num,Item,Memo,Quantity,Units,"
        "Item Rate,Amount,Ship Country\n"
        "21001,Item Receipt,IR10481,2023-03-14,Shenzhen Hightone,PO-10481,DCM-750-A,"
        "DC motor,2500,No.,34.00,85000.00,CN\n"
    )
    rpt = _rpt()
    rows = netsuite.parse_import_spine(csv_text, rpt)
    assert len(rows) == 1
    r = rows[0]
    assert r.join_ref == "PO-10481"          # Other Ref Num -> join key
    assert r.item == "DCM-750-A"             # item
    assert r.quantity == 2500                # quantity (int HTSUS units)
    assert r.unit_cost == Decimal("34.00")   # rate
    assert r.amount == Decimal("85000.00")   # amount
    assert r.transaction_date.isoformat() == "2023-03-14"   # trandate
    assert r.vendor == "Shenzhen Hightone"   # entity
    assert r.tranid == "IR10481"             # tranid / Document Number
    assert rpt.issues == []


def test_import_spine_json_suiteql_shape():
    json_text = (
        '{"items":[{"id":"21002","tranid":"IR10482","trandate":"2023-05-22",'
        '"entity":"Dongguan PowerCell","otherrefnum":"PO-10482","item":"PSU-240-B",'
        '"quantity":"1500","units":"No.","rate":"52.00","amount":"78000.00","shipcountry":"CN"}]}'
    )
    rows = netsuite.parse_import_spine(json_text, _rpt())
    assert len(rows) == 1
    assert rows[0].join_ref == "PO-10482"
    assert rows[0].unit_cost == Decimal("52.00")
    assert rows[0].quantity == 1500


def test_export_spine_csv_maps_real_fields():
    csv_text = (
        "Internal ID,Type,Document Number,Date,Name,Other Ref Num,Item,Memo,Quantity,Units,"
        "Item Rate,Amount,Ship Country,HTS Code\n"
        "31001,Item Fulfillment,IF50012,2023-09-12,Maple Systems,CI-50012,DCM-750-A,"
        "DC motor,2000,No.,41.00,82000.00,CA,8501.31.4000\n"
    )
    rows = netsuite.parse_export_spine(csv_text, _rpt())
    assert len(rows) == 1
    e = rows[0]
    assert e.join_ref == "CI-50012"          # commercial invoice ref -> AES join key
    assert e.unit_price == Decimal("41.00")  # rate -> value at export basis
    assert e.ship_country == "CA"            # shipcountry
    assert e.hint_hts == "8501.31.4000"      # item-master HTS hint


def test_amount_derived_from_rate_when_missing():
    csv_text = (
        "Type,Document Number,Date,Other Ref Num,Item,Quantity,Units,Item Rate,Ship Country\n"
        "Item Receipt,IR1,2023-03-14,PO-1,X,100,No.,10.00,CN\n"
    )
    rows = netsuite.parse_import_spine(csv_text, _rpt())
    assert rows[0].amount == Decimal("1000.00")   # rate*qty


def test_bad_rows_reported_not_crash():
    csv_text = (
        "Type,Document Number,Date,Other Ref Num,Item,Quantity,Units,Item Rate,Ship Country\n"
        "Item Receipt,IR1,not-a-date,PO-1,X,100,No.,10.00,CN\n"   # bad date -> dropped
        "Item Receipt,IR2,2023-03-14,PO-2,Y,-5,No.,10.00,CN\n"     # bad qty -> dropped
        "Item Receipt,IR3,2023-03-14,,Z,100,No.,10.00,CN\n"        # no ref but has tranid -> kept
    )
    rpt = _rpt()
    rows = netsuite.parse_import_spine(csv_text, rpt)
    assert len(rows) == 1                         # only IR3 survives (join_ref falls back to tranid)
    assert rows[0].join_ref == "IR3"
    fields = {i.field for i in rpt.issues if i.severity == "error"}
    assert {"trandate", "quantity"} <= fields


def test_negative_amount_parentheses_form():
    # NetSuite saved-search CSV renders credits as "(123.45)".
    csv_text = (
        "Type,Document Number,Date,Other Ref Num,Item,Quantity,Units,Item Rate,Amount,Ship Country\n"
        "Item Receipt,IR1,2023-03-14,PO-1,X,100,No.,10.00,(1000.00),CN\n"
    )
    rows = netsuite.parse_import_spine(csv_text, _rpt())
    assert rows[0].amount == Decimal("-1000.00")
