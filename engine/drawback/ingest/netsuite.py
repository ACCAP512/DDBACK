"""NetSuite saved-search / SuiteQL result-export parser (JSON and CSV).

Reads exports produced by a NetSuite saved search or a SuiteQL query against the standard
transaction tables, using the REAL NetSuite column ids you get back from those surfaces
(``tranid``, ``trandate``, ``entity``, ``item``, ``quantity``, ``rate``, ``amount``,
``shipcountry``, internal ``id`` …). NetSuite is the COMMERCIAL spine: it holds the item /
quantity / value / dates / parties of the transaction but NOT the duty or the customs entry —
those come from the broker overlay (``ingest.customs``).

Two spines:
  * IMPORT spine  — Purchase Orders / Item Receipts / Vendor Bills -> ``CommercialImport``.
  * EXPORT spine  — Sales Orders / Item Fulfillments / Invoices    -> ``CommercialExport``.

Accepts a file path, a directory (auto-discovers ``*import*`` / ``*export*`` files), or raw
text. JSON is the native saved-search/SuiteQL REST shape (``{"items":[{...}]}`` or a bare list);
CSV is the "Export - CSV" button output. Field-name variants seen across NetSuite account
configs are tolerated (see ``_FIELD_ALIASES``); every recoverable problem is reported to the
``DataQualityReport`` and the row kept or dropped accordingly.

Stdlib only (``csv`` / ``json``). NO network — the live SuiteQL/SuiteTalk seam is ``ingest.client``.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, List, Optional

from drawback.models import ZERO, DataQualityReport
from drawback.ingest.records import CommercialExport, CommercialImport

# ─────────────────────────────────────────────────────────────────────────────
# Real NetSuite field ids, with the common cross-account aliases.
# A NetSuite saved-search CSV/JSON labels columns by the field id; SuiteQL returns the
# column name. We accept both the raw id and the human "Label" form some exports emit.
# ─────────────────────────────────────────────────────────────────────────────
_FIELD_ALIASES = {
    # canonical -> tuple of accepted source keys (case-insensitive match applied below)
    "tranid": ("tranid", "Document Number", "documentnumber", "transactionnumber"),
    "trandate": ("trandate", "Date", "transactiondate"),
    "entity": ("entity", "Name", "entityname", "vendor", "customer"),
    "item": ("item", "Item", "itemid", "itemname"),
    "memo": ("memo", "Memo", "description", "Description", "item_description", "itemdescription"),
    "quantity": ("quantity", "Quantity", "quantityuom", "qty"),
    "units": ("units", "Units", "unit", "uom"),
    "rate": ("rate", "Rate", "unitprice", "unitcost", "Item Rate"),
    "amount": ("amount", "Amount", "amount_foreign", "fxamount", "grossamount"),
    "shipcountry": ("shipcountry", "Ship Country", "shippingcountry", "countryofdestination",
                    "country", "vendorcountry"),
    "internalid": ("id", "internalid", "Internal ID", "internal_id"),
    "recordtype": ("type", "recordtype", "Type", "transactiontype"),
    "joinref": ("otherrefnum", "Other Ref Num", "ponum", " ponumber", "purchaseorder",
                "createdfrom", "Created From", "ref", "reference", "invoicenumber",
                "commercialinvoice", "comm_invoice"),
    "hts": ("custcol_hts", "hts", "hts code", "htscode", "harmonizedcode", "harmonized code",
            "scheduleb", "schedule b", "schedulebcode"),
}


def _lower_keys(row: dict) -> dict:
    return {(k or "").strip().lower(): v for k, v in row.items()}


def _get(low: dict, canonical: str) -> Optional[str]:
    for key in _FIELD_ALIASES[canonical]:
        v = low.get(key.strip().lower())
        if v not in (None, ""):
            return str(v).strip()
    return None


def _dec(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        return None
    # NetSuite renders credits / negatives as "(123.45)" in some saved-search CSV exports.
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        return None
    return -d if neg else d


def _parse_date(value: Optional[str]) -> Optional[date]:
    s = (value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d-%b-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _int_qty(value: Optional[str]) -> Optional[int]:
    d = _dec(value)
    if d is None:
        return None
    # Commercial quantities can arrive as "1000.0"; HTSUS units are integers (A-16 seam).
    if d != d.to_integral_value():
        return None  # caller decides whether a fractional commercial qty is fatal
    return int(d)


# ─────────────────────────────────────────────────────────────────────────────
# Source loading: path | directory | raw text -> list[dict]
# ─────────────────────────────────────────────────────────────────────────────
def _looks_like_path(s: str) -> bool:
    return ("\n" not in s) and (s.endswith(".csv") or s.endswith(".json"))


def _rows_from_text(text: str) -> List[dict]:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            # Saved-search REST / SuiteQL shapes: {"items":[...]} or {"results":[...]}.
            for key in ("items", "results", "rows", "data"):
                if isinstance(data.get(key), list):
                    return list(data[key])
            return [data]
        if isinstance(data, list):
            return list(data)
        return []
    return list(csv.DictReader(io.StringIO(text)))


def _load_rows(source, report: DataQualityReport, label: str) -> List[dict]:
    if isinstance(source, (str, Path)) and (isinstance(source, Path) or _looks_like_path(str(source))):
        p = Path(source)
        if not p.exists():
            report.add("error", -1, label, "NetSuite source file not found: %s" % p)
            return []
        return _rows_from_text(p.read_text())
    return _rows_from_text(str(source))


def _discover(directory, patterns: Iterable[str]) -> Optional[Path]:
    d = Path(directory)
    if not d.is_dir():
        return None
    for pat in patterns:
        hits = sorted(d.glob(pat))
        if hits:
            return hits[0]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT spine: PO / Item Receipt / Vendor Bill -> CommercialImport
# ─────────────────────────────────────────────────────────────────────────────
def parse_import_spine(source, report: DataQualityReport) -> List[CommercialImport]:
    rows = _load_rows(source, report, "netsuite_imports")
    out: List[CommercialImport] = []
    for idx, raw in enumerate(rows, start=2):
        low = _lower_keys(raw)
        join_ref = _get(low, "joinref") or _get(low, "tranid") or ""
        item = _get(low, "item") or ""
        qty = _int_qty(_get(low, "quantity"))
        rate = _dec(_get(low, "rate"))
        amount = _dec(_get(low, "amount"))
        tdate = _parse_date(_get(low, "trandate"))

        if not join_ref:
            report.add("error", idx, "join_ref",
                       "NetSuite import line has no PO/invoice ref or document number"); continue
        if not item:
            report.add("warning", idx, "item", "NetSuite import line missing item id")
        if qty is None or qty <= 0:
            report.add("error", idx, "quantity",
                       "invalid NetSuite import quantity %r" % _get(low, "quantity")); continue
        if tdate is None:
            report.add("error", idx, "trandate",
                       "unparseable NetSuite transaction date %r" % _get(low, "trandate")); continue
        if amount is None and rate is None:
            report.add("warning", idx, "amount",
                       "NetSuite import line carries neither rate nor amount (entered value will lean on customs)")

        if amount is None and rate is not None:
            amount = (rate * Decimal(qty))
        if rate is None and amount is not None and qty:
            rate = amount / Decimal(qty)

        out.append(CommercialImport(
            join_ref=join_ref, item=item,
            description=_get(low, "memo") or item,
            quantity=qty, unit_of_measure=_get(low, "units") or "No.",
            unit_cost=rate if rate is not None else ZERO,
            amount=amount if amount is not None else ZERO,
            transaction_date=tdate,
            vendor=_get(low, "entity") or "",
            vendor_country=(_get(low, "shipcountry") or "CN"),
            tranid=_get(low, "tranid") or "",
            internal_id=_get(low, "internalid") or "",
            record_type=(_get(low, "recordtype") or "itemreceipt").lower(),
            hint_hts=_get(low, "hts"),
            source_row=idx,
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT spine: SO / Item Fulfillment / Invoice -> CommercialExport
# ─────────────────────────────────────────────────────────────────────────────
def parse_export_spine(source, report: DataQualityReport) -> List[CommercialExport]:
    rows = _load_rows(source, report, "netsuite_exports")
    out: List[CommercialExport] = []
    for idx, raw in enumerate(rows, start=2):
        low = _lower_keys(raw)
        join_ref = _get(low, "joinref") or _get(low, "tranid") or ""
        item = _get(low, "item") or ""
        qty = _int_qty(_get(low, "quantity"))
        rate = _dec(_get(low, "rate"))
        amount = _dec(_get(low, "amount"))
        tdate = _parse_date(_get(low, "trandate"))

        if not join_ref:
            report.add("error", idx, "join_ref",
                       "NetSuite export line has no SO/invoice ref or document number"); continue
        if qty is None or qty <= 0:
            report.add("error", idx, "quantity",
                       "invalid NetSuite export quantity %r" % _get(low, "quantity")); continue
        if tdate is None:
            report.add("error", idx, "trandate",
                       "unparseable NetSuite export date %r" % _get(low, "trandate")); continue
        if rate is None and amount is not None and qty:
            rate = amount / Decimal(qty)
        if rate is None:
            report.add("warning", idx, "rate",
                       "NetSuite export line missing rate/amount; value-at-export will be 0 until priced")

        out.append(CommercialExport(
            join_ref=join_ref, item=item,
            description=_get(low, "memo") or item,
            quantity=qty, unit_of_measure=_get(low, "units") or "No.",
            unit_price=rate if rate is not None else ZERO,
            amount=amount if amount is not None else ZERO,
            transaction_date=tdate,
            customer=_get(low, "entity") or "",
            ship_country=(_get(low, "shipcountry") or "US"),
            tranid=_get(low, "tranid") or "",
            internal_id=_get(low, "internalid") or "",
            record_type=(_get(low, "recordtype") or "itemfulfillment").lower(),
            hint_hts=_get(low, "hts"),
            source_row=idx,
        ))
    return out


def parse_import_dir(directory, report: DataQualityReport) -> List[CommercialImport]:
    path = _discover(directory, ("*import*.json", "*import*.csv", "*receipt*.json", "*receipt*.csv"))
    if path is None:
        report.add("error", -1, "netsuite_imports",
                   "no NetSuite import-spine file (*import*/*receipt*) found in %s" % directory)
        return []
    return parse_import_spine(path, report)


def parse_export_dir(directory, report: DataQualityReport) -> List[CommercialExport]:
    path = _discover(directory, ("*export*.json", "*export*.csv", "*fulfill*.json", "*fulfill*.csv",
                                 "*sales*.json", "*sales*.csv"))
    if path is None:
        report.add("error", -1, "netsuite_exports",
                   "no NetSuite export-spine file (*export*/*fulfill*/*sales*) found in %s" % directory)
        return []
    return parse_export_spine(path, report)
