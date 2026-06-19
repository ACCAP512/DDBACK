"""CSV ingestion + validation + data-quality reporting (FR1.2).

Parses the ACE/ITRAC-like import file and the EEI/invoice-like export file into the canonical models,
surfacing problems (missing fields, unparseable HTS/dates, unknown HTS codes, bad numbers) rather than
silently guessing. Rows with errors are DROPPED (and reported); rows with warnings are kept and flagged.

Accepts file paths or raw CSV text (for the API upload path).
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional

from drawback.models import (
    ZERO, ChargeType, Dataset, DataQualityReport, ExportAction, ExportLine, ImportLine,
)
from drawback.data.hts_reference import DEFAULT_REFERENCE
from drawback.rules.hts import normalize_hts

_CHARGE_COLUMNS = {
    "duty_base": ChargeType.BASE_DUTY, "duty_301": ChargeType.SECTION_301,
    "duty_232": ChargeType.SECTION_232, "duty_ieepa": ChargeType.IEEPA,
    "mpf": ChargeType.MPF, "hmf": ChargeType.HMF, "ad_cvd": ChargeType.AD_CVD,
    "excise": ChargeType.EXCISE,
}


def _rows(source: str | Path) -> Iterable[dict]:
    text = Path(source).read_text() if isinstance(source, Path) or _looks_like_path(source) else source
    return list(csv.DictReader(io.StringIO(text)))


def _looks_like_path(s: str) -> bool:
    return ("\n" not in s) and s.endswith(".csv")


def _dec(value: str) -> Optional[Decimal]:
    try:
        d = Decimal((value or "0").strip() or "0")
        return d
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_imports(source: str | Path, report: DataQualityReport, ref=DEFAULT_REFERENCE) -> list[ImportLine]:
    out: list[ImportLine] = []
    for idx, row in enumerate(_rows(source), start=2):  # row 1 = header
        entry = (row.get("entry_number") or "").strip()
        hts10 = normalize_hts(row.get("hts10") or "")
        imp_date = _parse_date(row.get("import_date", ""))
        qty_raw = _dec(row.get("quantity", ""))
        ev = _dec(row.get("entered_value", ""))

        if not entry:
            report.add("error", idx, "entry_number", "missing entry number"); report.imports_dropped += 1; continue
        if len(hts10) < 8:
            report.add("error", idx, "hts10", f"HTS '{row.get('hts10')}' has fewer than 8 digits"); report.imports_dropped += 1; continue
        if imp_date is None:
            report.add("error", idx, "import_date", f"unparseable import date '{row.get('import_date')}'"); report.imports_dropped += 1; continue
        if qty_raw is None or qty_raw <= 0:
            report.add("error", idx, "quantity", f"invalid quantity '{row.get('quantity')}'"); report.imports_dropped += 1; continue
        if ev is None or ev < 0:
            report.add("error", idx, "entered_value", f"invalid entered value '{row.get('entered_value')}'"); report.imports_dropped += 1; continue
        if not ref.is_known(hts10):
            report.add("warning", idx, "hts10", f"HTS {hts10[:8]} not in reference — base/301 rates unknown (treated as 0)")

        charges: dict[ChargeType, Decimal] = {}
        for col, ctype in _CHARGE_COLUMNS.items():
            amt = _dec(row.get(col, "0"))
            if amt is None:
                report.add("warning", idx, col, f"unparseable charge '{row.get(col)}' treated as 0"); amt = ZERO
            if amt > 0:
                charges[ctype] = amt

        out.append(ImportLine(
            entry_number=entry, line_number=int(_dec(row.get("line_number", "1")) or 1),
            importer_id=(row.get("importer_id") or "").strip(), hts10=hts10,
            description=(row.get("description") or "").strip(), import_date=imp_date,
            entry_date=_parse_date(row.get("entry_date", "")) or imp_date,
            quantity=int(qty_raw), unit_of_measure=(row.get("uom") or "No.").strip(),
            entered_value=ev, charges=charges,
            country_of_origin=(row.get("country_of_origin") or "CN").strip(),
            liquidated=(row.get("liquidated") or "Y").strip().upper() != "N", source_row=idx,
        ))
    report.imports_parsed = len(out)
    return out


def parse_exports(source: str | Path, report: DataQualityReport, ref=DEFAULT_REFERENCE) -> list[ExportLine]:
    out: list[ExportLine] = []
    for idx, row in enumerate(_rows(source), start=2):
        ref_no = (row.get("reference") or "").strip()
        hts10 = normalize_hts(row.get("hts10") or "")
        exp_date = _parse_date(row.get("export_date", ""))
        qty = _dec(row.get("quantity", ""))
        vpu = _dec(row.get("value_per_unit", ""))

        if not ref_no:
            report.add("error", idx, "reference", "missing export reference"); report.exports_dropped += 1; continue
        if len(hts10) < 8:
            report.add("error", idx, "hts10", f"HTS '{row.get('hts10')}' has fewer than 8 digits"); report.exports_dropped += 1; continue
        if exp_date is None:
            report.add("error", idx, "export_date", f"unparseable export date '{row.get('export_date')}'"); report.exports_dropped += 1; continue
        if qty is None or qty <= 0:
            report.add("error", idx, "quantity", f"invalid quantity '{row.get('quantity')}'"); report.exports_dropped += 1; continue
        if vpu is None or vpu < 0:
            report.add("error", idx, "value_per_unit", f"invalid value per unit '{row.get('value_per_unit')}'"); report.exports_dropped += 1; continue

        line_raw = (row.get("direct_id_line") or "").strip()
        out.append(ExportLine(
            reference=ref_no, hts10=hts10, description=(row.get("description") or "").strip(),
            export_date=exp_date, quantity=int(qty), unit_of_measure=(row.get("uom") or "No.").strip(),
            value_per_unit=vpu,
            action=ExportAction.DESTROY if (row.get("action") or "").strip().lower() == "destroy" else ExportAction.EXPORT,
            destination_country=(row.get("destination_country") or "US").strip(),
            has_export_proof=(row.get("has_export_proof") or "Y").strip().upper() != "N",
            proof_kind=(row.get("proof_kind") or "bill_of_lading").strip(),
            recovered_value_per_unit=_dec(row.get("recovered_value_per_unit", "0")) or ZERO,
            direct_id_entry=(row.get("direct_id_entry") or "").strip() or None,
            direct_id_line=int(line_raw) if line_raw.isdigit() else None, source_row=idx,
        ))
    report.exports_parsed = len(out)
    return out


def parse_dataset(import_source: str | Path, export_source: str | Path, ref=DEFAULT_REFERENCE) -> Dataset:
    report = DataQualityReport()
    imports = parse_imports(import_source, report, ref)
    exports = parse_exports(export_source, report, ref)
    importer_id = imports[0].importer_id if imports else ""
    return Dataset(imports=imports, exports=exports, data_quality=report, importer_id=importer_id)
