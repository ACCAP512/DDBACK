"""Customs overlay parser — the duty/proof data NetSuite does NOT hold.

Two real delivered formats:

(a) CBP Form 7501 / ACE entry-summary line export (the "ACE Reports / ITRAC CSV/Excel" surface,
    RESEARCH Q14/Q18). One row per entry-summary line, with the entry number, 10-digit HTSUS,
    entered value, and the duty/fee components a broker breaks out. Header labels follow the
    7501 block/column names brokers actually emit, e.g. ``Entry Number`` (blk 1),
    ``Import Date`` (blk 11), ``Line`` (col 31), ``HTSUS`` (col 33A), ``Entered Value`` (col 36A),
    ``Duty`` (col 38 base), ``MPF`` (acct 499), ``HMF`` (acct 501), ``Sec 301`` / ``Sec 232``
    where the broker splits them, ``Importer of Record`` (blk 27). Fees are read BY column /
    accounting code, never inferred from a single block-44 total.

(b) AES / EEI export filing export (15 CFR 30.6, RESEARCH Q15). One row per commodity line, with
    the ``ITN`` (the proof token AES returns), ``Schedule B`` / ``HTSUS`` 10-digit, value at port
    of export, ``Date of Export``, ``USPPI`` (EIN), ``Country of Ultimate Destination`` (ISO),
    and the commercial-invoice / shipment reference + ``Bill of Lading`` number that ties the EEI
    back to the NetSuite sale. A B/L reference is an accepted documentary export proof (CATAIR
    BOL Indicator + SCAC, RESEARCH Q15/Q17).

Duty/fee component -> engine ``ChargeType`` mapping lives in ``_CHARGE_HEADER_MAP`` and is
documented (with [VERIFIED]/[INFERRED]/[GUESS] tags) in ``docs/INGESTION.md``.

Stdlib only (``csv`` / ``json``). NO OCR (no PDF 7501 path), NO network.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from drawback.models import ZERO, ChargeType, DataQualityReport
from drawback.rules.hts import normalize_hts


# ─────────────────────────────────────────────────────────────────────────────
# Customs overlay records (the duty + the proof). Joined onto the commercial spine.
# ─────────────────────────────────────────────────────────────────────────────
from dataclasses import dataclass


@dataclass
class CustomsEntryLine:
    """One CBP 7501 / ACE entry-summary line: the authoritative customs+duty facts for an import.

    The ``join_ref`` is what the broker keys the entry to on the commercial side (the PO number
    or commercial-invoice number printed on the 7501 / carried in the ACE export). The duty
    components are already split into engine ``ChargeType`` buckets.
    """

    entry_number: str                                  # blk 1 (XXX-NNNNNNN-N)
    line_number: int                                   # col 31
    importer_of_record: str                            # blk 27 (IRS/EIN)
    hts10: str                                         # col 33A (10-digit, normalized)
    description: str                                   # col 32
    import_date: date                                  # blk 11 — starts the 5-yr clock
    entry_date: Optional[date]                         # blk 7
    quantity: int                                      # col 35 net qty in HTSUS units
    unit_of_measure: str                               # col 35 UoM
    entered_value: Decimal                             # col 36A
    charges: Dict[ChargeType, Decimal]                 # col 38 + Other Fee Summary, by code
    country_of_origin: str = "CN"                      # blk 10
    liquidated: bool = True                            # A-14
    join_ref: str = ""                                 # PO / commercial-invoice ref (join key)
    source_row: int = -1


@dataclass
class AesExportRecord:
    """One AES/EEI commodity line: the export-proof overlay (ITN + destination + value).

    ``join_ref`` is the commercial-invoice / shipment reference that ties this EEI line to the
    NetSuite Sales Order / Item Fulfillment. ``itn`` is the proof token; a ``bill_of_lading`` is
    the documentary fallback proof.
    """

    itn: str                                           # AES Internal Transaction Number (proof)
    hts10: str                                         # Schedule B or HTSUS (10-digit, normalized)
    description: str
    export_date: date                                  # date of export
    quantity: int
    unit_of_measure: str
    value_at_export: Decimal                           # value at U.S. port of export (line total)
    usppi_id: str = ""                                 # USPPI EIN
    destination_country: str = "US"                    # country of ultimate destination (ISO)
    bill_of_lading: str = ""                           # B/L / AWB number (documentary proof)
    join_ref: str = ""                                 # commercial invoice / shipment ref
    source_row: int = -1

    @property
    def value_per_unit(self) -> Decimal:
        if self.quantity:
            return self.value_at_export / Decimal(self.quantity)
        return ZERO


# ─────────────────────────────────────────────────────────────────────────────
# 7501 / ACE duty-and-fee column -> ChargeType.  Header matching is case/punct-insensitive
# (see _norm_header). Multiple aliases per component because broker ACE exports differ.
#   [VERIFIED] base duty (col 38), MPF (acct 499), HMF (acct 501), Sec 301, AD, CVD.
#   [INFERRED] Sec 232 / Sec 122 / IEEPA bucket names (brokers haven't standardized columns).
# ─────────────────────────────────────────────────────────────────────────────
_CHARGE_HEADER_MAP = {
    ChargeType.BASE_DUTY: ("duty", "base duty", "duty amount", "regular duty", "ordinary duty",
                           "col38 duty", "duty_38"),
    ChargeType.SECTION_301: ("sec 301", "section 301", "301 duty", "301", "ch99 301", "duty 301"),
    ChargeType.SECTION_232: ("sec 232", "section 232", "232 duty", "232", "duty 232"),
    ChargeType.SECTION_122: ("sec 122", "section 122", "122 duty", "122"),
    ChargeType.IEEPA: ("ieepa", "ieepa duty", "reciprocal", "fentanyl", "duty ieepa"),
    ChargeType.MPF: ("mpf", "merchandise processing fee", "acct 499", "499", "mpf amount"),
    ChargeType.HMF: ("hmf", "harbor maintenance fee", "acct 501", "501", "hmf amount"),
    ChargeType.AD_CVD: ("ad/cvd", "ad cvd", "adcvd", "antidumping", "countervailing",
                        "acct 012", "acct 013", "ad", "cvd"),
    ChargeType.EXCISE: ("excise", "ir tax", "i.r. tax", "irc tax", "federal excise"),
}

_ENTRY_NUMBER_HEADERS = ("entry number", "entry no", "entry", "entry summary number",
                         "entryno", "entry_no", "filer entry")
_LINE_HEADERS = ("line", "line no", "line number", "es line", "line item", "lineno")
_HTS_HEADERS = ("htsus", "hts", "hts10", "hts number", "tariff", "hts code", "tariff number")
_DESC_HEADERS = ("description", "desc", "commodity description", "article description")
_IMPDATE_HEADERS = ("import date", "date of importation", "importation date", "imp date")
_ENTRYDATE_HEADERS = ("entry date", "date of entry")
_QTY_HEADERS = ("quantity", "net quantity", "qty", "hts quantity", "quantity 1", "net qty")
_UOM_HEADERS = ("uom", "unit", "units", "unit of measure", "quantity uom", "hts uom")
_EV_HEADERS = ("entered value", "entered_value", "customs value", "value", "line value")
_IOR_HEADERS = ("importer of record", "importer", "ior", "importer number", "ior number",
                "importer of record number", "irs number")
_COO_HEADERS = ("country of origin", "coo", "origin", "country")
_LIQ_HEADERS = ("liquidated", "liquidation", "liq status", "liquidation status", "final liquidation")
_JOINREF_HEADERS = ("po number", "po", "po no", "purchase order", "commercial invoice",
                    "invoice number", "invoice", "reference", "ref", "comm invoice")

# AES / EEI headers (15 CFR 30.6)
_ITN_HEADERS = ("itn", "internal transaction number", "aes itn", "proof", "aes number")
_SCHEDB_HEADERS = ("schedule b", "scheduleb", "schedule b number", "hts", "htsus", "hts10",
                   "commodity classification", "b/hts", "classification")
_EXPDATE_HEADERS = ("date of export", "export date", "departure date", "on-board date",
                    "shipment date", "exp date")
_EXPVAL_HEADERS = ("value", "value at export", "value at port of export", "fob value",
                   "line value", "export value")
_USPPI_HEADERS = ("usppi", "usppi id", "usppi ein", "usppi number", "ein")
_DEST_HEADERS = ("country of ultimate destination", "ultimate destination", "destination",
                 "destination country", "country", "dest")
_BOL_HEADERS = ("bill of lading", "bol", "b/l", "bill of lading number", "awb", "air waybill",
                "bol number")
_EXP_JOINREF_HEADERS = ("commercial invoice", "invoice number", "invoice", "shipment reference",
                        "shipment ref", "reference", "ref", "so number", "sales order")


def _norm_header(h: str) -> str:
    return "".join(ch for ch in (h or "").lower() if ch.isalnum() or ch == " ").strip()


def _build_index(fieldnames: Iterable[str]) -> Dict[str, str]:
    """Map normalized header text -> the original column key, for tolerant lookup."""
    idx: Dict[str, str] = {}
    for raw in fieldnames or []:
        idx[_norm_header(raw)] = raw
    return idx


def _pick(row: dict, index: Dict[str, str], headers: Iterable[str]) -> Optional[str]:
    for h in headers:
        col = index.get(_norm_header(h))
        if col is not None:
            v = row.get(col)
            if v not in (None, ""):
                return str(v).strip()
    return None


def _dec(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        return None
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
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _looks_like_path(s: str) -> bool:
    return ("\n" not in s) and (s.endswith(".csv") or s.endswith(".json"))


def _csv_rows(text: str):
    reader = csv.DictReader(io.StringIO(text))
    return reader.fieldnames, list(reader)


def _json_rows(text: str):
    data = json.loads(text)
    rows: List[dict]
    if isinstance(data, dict):
        rows = None
        for key in ("items", "results", "rows", "data", "lines"):
            if isinstance(data.get(key), list):
                rows = list(data[key]); break
        if rows is None:
            rows = [data]
    elif isinstance(data, list):
        rows = list(data)
    else:
        rows = []
    fieldnames = list(rows[0].keys()) if rows else []
    return fieldnames, rows


def _load(source, report: DataQualityReport, label: str):
    if isinstance(source, (str, Path)) and (isinstance(source, Path) or _looks_like_path(str(source))):
        p = Path(source)
        if not p.exists():
            report.add("error", -1, label, "customs source file not found: %s" % p)
            return [], []
        text = p.read_text()
    else:
        text = str(source)
    if text.lstrip().startswith("{") or text.lstrip().startswith("["):
        return _json_rows(text)
    return _csv_rows(text)


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
# (a) 7501 / ACE entry-summary parser
# ─────────────────────────────────────────────────────────────────────────────
def parse_entry_summaries(source, report: DataQualityReport) -> List[CustomsEntryLine]:
    fieldnames, rows = _load(source, report, "ace_entry_summary")
    index = _build_index(fieldnames)
    out: List[CustomsEntryLine] = []
    for idx, row in enumerate(rows, start=2):
        entry = _pick(row, index, _ENTRY_NUMBER_HEADERS) or ""
        hts10 = normalize_hts(_pick(row, index, _HTS_HEADERS) or "")
        imp_date = _parse_date(_pick(row, index, _IMPDATE_HEADERS))
        qty = _dec(_pick(row, index, _QTY_HEADERS))
        ev = _dec(_pick(row, index, _EV_HEADERS))

        if not entry:
            report.add("error", idx, "entry_number", "7501 line missing entry number"); continue
        if len(hts10) < 8:
            report.add("error", idx, "hts10",
                       "7501 HTSUS %r has fewer than 8 digits" % _pick(row, index, _HTS_HEADERS)); continue
        if imp_date is None:
            report.add("error", idx, "import_date",
                       "unparseable 7501 import date %r" % _pick(row, index, _IMPDATE_HEADERS)); continue
        if qty is None or qty <= 0:
            report.add("error", idx, "quantity",
                       "invalid 7501 net quantity %r" % _pick(row, index, _QTY_HEADERS)); continue
        if ev is None or ev < 0:
            report.add("error", idx, "entered_value",
                       "invalid 7501 entered value %r" % _pick(row, index, _EV_HEADERS)); continue

        charges: Dict[ChargeType, Decimal] = {}
        for ctype, hdrs in _CHARGE_HEADER_MAP.items():
            amt = _dec(_pick(row, index, hdrs))
            if amt is not None and amt > 0:
                charges[ctype] = amt

        liq_raw = (_pick(row, index, _LIQ_HEADERS) or "Y").strip().upper()
        liquidated = liq_raw not in ("N", "NO", "OPEN", "UNLIQUIDATED", "PENDING", "FALSE")

        line_no = _dec(_pick(row, index, _LINE_HEADERS))
        out.append(CustomsEntryLine(
            entry_number=entry, line_number=int(line_no) if line_no is not None else 1,
            importer_of_record=_pick(row, index, _IOR_HEADERS) or "",
            hts10=hts10, description=_pick(row, index, _DESC_HEADERS) or "",
            import_date=imp_date, entry_date=_parse_date(_pick(row, index, _ENTRYDATE_HEADERS)),
            quantity=int(qty), unit_of_measure=_pick(row, index, _UOM_HEADERS) or "No.",
            entered_value=ev, charges=charges,
            country_of_origin=_pick(row, index, _COO_HEADERS) or "CN",
            liquidated=liquidated,
            join_ref=_pick(row, index, _JOINREF_HEADERS) or "",
            source_row=idx,
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# (b) AES / EEI export-proof parser
# ─────────────────────────────────────────────────────────────────────────────
def parse_aes_eei(source, report: DataQualityReport) -> List[AesExportRecord]:
    fieldnames, rows = _load(source, report, "aes_eei")
    index = _build_index(fieldnames)
    out: List[AesExportRecord] = []
    for idx, row in enumerate(rows, start=2):
        itn = _pick(row, index, _ITN_HEADERS) or ""
        hts10 = normalize_hts(_pick(row, index, _SCHEDB_HEADERS) or "")
        exp_date = _parse_date(_pick(row, index, _EXPDATE_HEADERS))
        qty = _dec(_pick(row, index, _QTY_HEADERS))
        val = _dec(_pick(row, index, _EXPVAL_HEADERS))
        bol = _pick(row, index, _BOL_HEADERS) or ""

        # Proof token: an ITN OR a B/L number is acceptable documentary export proof (Q15/Q17).
        if not itn and not bol:
            report.add("warning", idx, "itn",
                       "AES/EEI line has neither ITN nor bill-of-lading — export proof will be missing")
        if len(hts10) < 8:
            report.add("error", idx, "hts10",
                       "AES Schedule B/HTSUS %r has fewer than 8 digits"
                       % _pick(row, index, _SCHEDB_HEADERS)); continue
        if exp_date is None:
            report.add("error", idx, "export_date",
                       "unparseable AES date of export %r" % _pick(row, index, _EXPDATE_HEADERS)); continue
        if qty is None or qty <= 0:
            report.add("error", idx, "quantity",
                       "invalid AES quantity %r" % _pick(row, index, _QTY_HEADERS)); continue
        if val is None or val < 0:
            report.add("error", idx, "value",
                       "invalid AES value at export %r" % _pick(row, index, _EXPVAL_HEADERS)); continue

        out.append(AesExportRecord(
            itn=itn, hts10=hts10, description=_pick(row, index, _DESC_HEADERS) or "",
            export_date=exp_date, quantity=int(qty),
            unit_of_measure=_pick(row, index, _UOM_HEADERS) or "No.",
            value_at_export=val, usppi_id=_pick(row, index, _USPPI_HEADERS) or "",
            destination_country=_pick(row, index, _DEST_HEADERS) or "US",
            bill_of_lading=bol,
            join_ref=_pick(row, index, _EXP_JOINREF_HEADERS) or "",
            source_row=idx,
        ))
    return out


def parse_entry_dir(directory, report: DataQualityReport) -> List[CustomsEntryLine]:
    path = _discover(directory, ("*7501*.csv", "*7501*.json", "*entry*summary*.csv",
                                 "*entry*summary*.json", "*ace*.csv", "*ace*.json",
                                 "*entry*.csv", "*entry*.json"))
    if path is None:
        report.add("error", -1, "ace_entry_summary",
                   "no 7501/ACE entry-summary file (*7501*/*entry*/*ace*) found in %s" % directory)
        return []
    return parse_entry_summaries(path, report)


def parse_aes_dir(directory, report: DataQualityReport) -> List[AesExportRecord]:
    path = _discover(directory, ("*aes*.csv", "*aes*.json", "*eei*.csv", "*eei*.json",
                                 "*export*proof*.csv", "*export*proof*.json"))
    if path is None:
        report.add("error", -1, "aes_eei",
                   "no AES/EEI export-proof file (*aes*/*eei*/*export*proof*) found in %s" % directory)
        return []
    return parse_aes_eei(path, report)
