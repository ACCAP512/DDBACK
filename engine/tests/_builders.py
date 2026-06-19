"""Concise builders for tests. Not a pytest module (leading underscore)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from drawback.models import ChargeType, Dataset, DataQualityReport, ExportLine, ImportLine


def D(x) -> Decimal:
    return Decimal(str(x))


def imp(entry, hts10, qty, charges, import_date, *, liquidated=True, line=1, value=None) -> ImportLine:
    # Coerce string charge keys to ChargeType (the model's contract is dict[ChargeType, Decimal]).
    ch = {(ChargeType(k) if isinstance(k, str) else k): D(v) for k, v in charges.items()}
    return ImportLine(
        entry_number=entry, line_number=line, importer_id="47-3319008", hts10=hts10,
        description="test", import_date=import_date, quantity=qty, unit_of_measure="No.",
        entered_value=D(value if value is not None else sum(ch.values())),
        charges=ch, liquidated=liquidated,
    )


def exp(ref, hts10, qty, vpu, export_date, *, proof=True, direct_entry=None, direct_line=None,
        recovered=0) -> ExportLine:
    return ExportLine(
        reference=ref, hts10=hts10, description="test", export_date=export_date, quantity=qty,
        unit_of_measure="No.", value_per_unit=D(vpu), has_export_proof=proof,
        direct_id_entry=direct_entry, direct_id_line=direct_line, recovered_value_per_unit=D(recovered),
    )


def dataset(imports, exports) -> Dataset:
    return Dataset(imports=imports, exports=exports,
                   data_quality=DataQualityReport(imports_parsed=len(imports), exports_parsed=len(exports)))


# Common charge bundles (per line totals)
def charges_301(value, base_rate, s301_rate=Decimal("0.25")):
    v = D(value)
    return {
        ChargeType.BASE_DUTY: v * D(base_rate),
        ChargeType.SECTION_301: v * s301_rate,
        ChargeType.MPF: v * D("0.003464"),
        ChargeType.HMF: v * D("0.00125"),
    }
