"""Synthetic data generator (DECISIONS D-010; PRD §5.2).

Primary persona: a mid-market electronics / industrial-hardware importer-exporter ("Apex Electronics
Importing LLC") that imports Section-301 Chinese components and exports finished goods / re-exports
unsold inventory. Deterministic via ``seed``. Emits realistic messiness so the engine's matching,
exclusion, and conservatism logic are VISIBLE and testable:
  * multi-year spread incl. some genuinely out-of-window imports,
  * some lines carrying ineligible Section-232 / IEEPA layers,
  * some not-yet-liquidated recent entries,
  * a mix of substitution exports, direct-ID re-exports (full recovery), and missing-proof exports,
  * "other"-basket HTS exercising the 10-digit fallback and the no-substitution edge case,
  * some exports with no matching import subheading.

All synthetic data is clearly labelled and isolated from any real-data path. ``write_csvs`` renders it
in ACE/ITRAC-like CSV so the upload->parse path runs on the same data (clean swap-in seam).
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from drawback.config import tariff_eligibility as cfg
from drawback.models import (
    ZERO, ChargeType, Dataset, DataQualityReport, ExportLine, ImportLine, ExportAction,
)
from drawback.data.hts_reference import DEFAULT_REFERENCE as REF

IMPORTER_NAME = "Apex Electronics Importing LLC"
IMPORTER_EIN = "47-3319008"

_301_CODES = [c for c in REF.known_codes() if REF.section_301_rate(c) > 0 and not REF.begins_with_other(c)]
_OTHER_CODES = [c for c in REF.known_codes() if REF.begins_with_other(c)]


def _money(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _charges_for(hts8: str, entered_value: Decimal, *, add_232: bool, add_ieepa: bool) -> dict:
    ch = {
        ChargeType.BASE_DUTY: _money(REF.base_duty_rate(hts8) * entered_value),
        ChargeType.SECTION_301: _money(REF.section_301_rate(hts8) * entered_value),
        ChargeType.MPF: _money(Decimal("0.003464") * entered_value),
        ChargeType.HMF: _money(Decimal("0.00125") * entered_value),
    }
    if add_232:
        ch[ChargeType.SECTION_232] = _money(Decimal("0.25") * entered_value)  # ineligible
    if add_ieepa:
        ch[ChargeType.IEEPA] = _money(Decimal("0.10") * entered_value)        # CAPE track, not drawback
    return {k: v for k, v in ch.items() if v > 0}


def generate(seed: int = 42, scale: str = "demo", as_of: date = cfg.AS_OF) -> Dataset:
    rng = random.Random(seed)
    n_imports = {"tiny": 12, "demo": 220, "medium": 1200, "large": 4000}.get(scale, 220)

    earliest = as_of - timedelta(days=int(5.6 * 365))   # a bit before the 5-yr window -> some out-of-window
    span_days = (as_of - earliest).days

    imports: list[ImportLine] = []
    for i in range(n_imports):
        hts = rng.choice(_301_CODES)
        hts10 = hts + f"{rng.randint(0, 99):02d}"
        qty = rng.choice([50, 100, 250, 400, 600, 1000, 1500, 2500])
        unit_val = Decimal(rng.choice([8, 15, 22, 35, 60, 90, 140, 220, 480, 900]))
        entered_value = _money(unit_val * qty)
        imp_date = earliest + timedelta(days=rng.randint(0, span_days))
        add_232 = rng.random() < 0.12
        add_ieepa = rng.random() < 0.08
        # recent imports (< ~10 months old) often not yet finally liquidated
        liquidated = not (imp_date > as_of - timedelta(days=300) and rng.random() < 0.6)
        imports.append(ImportLine(
            entry_number=f"APX-{2000 + i:07d}", line_number=1, importer_id=IMPORTER_EIN,
            hts10=hts10, description=REF.description(hts), import_date=imp_date,
            entry_date=imp_date + timedelta(days=rng.randint(0, 5)),
            quantity=qty, unit_of_measure="No.", entered_value=entered_value,
            charges=_charges_for(hts, entered_value, add_232=add_232, add_ieepa=add_ieepa),
            country_of_origin="CN", liquidated=liquidated, source_row=i + 2,
        ))

    exports: list[ExportLine] = []
    ref_no = 90000

    def _new_ref() -> str:
        nonlocal ref_no
        ref_no += 1
        return f"INV-{ref_no}"

    # Most exports correspond to imports (re-export of unsold inventory or finished-good export).
    in_window_imports = [im for im in imports if im.import_date > as_of - timedelta(days=5 * 365)]
    for im in in_window_imports:
        if rng.random() > 0.80:
            continue  # not every import is later exported
        # export some/most of the imported quantity, after import, within window
        export_qty = max(1, int(im.quantity * rng.choice([0.4, 0.6, 0.8, 1.0])))
        latest_ok = min(as_of, im.import_date + timedelta(days=5 * 365))
        if latest_ok <= im.import_date:
            continue
        exp_date = im.import_date + timedelta(days=rng.randint(20, max(21, (latest_ok - im.import_date).days)))
        unit_val = (im.entered_value / Decimal(im.quantity)) * Decimal(str(rng.choice([0.85, 0.95, 1.0, 1.1, 1.25])))
        is_direct = rng.random() < 0.45                       # re-export of the SAME goods -> (j)(1)
        has_proof = rng.random() > 0.18                        # ~18% missing proof -> potential
        exports.append(ExportLine(
            reference=_new_ref(), hts10=im.hts10, description=im.description, export_date=exp_date,
            quantity=export_qty, unit_of_measure="No.", value_per_unit=_money(unit_val),
            action=ExportAction.EXPORT, destination_country=rng.choice(["CA", "MX", "GB", "DE", "JP"]),
            has_export_proof=has_proof, proof_kind="bill_of_lading" if has_proof else "none",
            direct_id_entry=im.entry_number if is_direct else None,
            direct_id_line=im.line_number if is_direct else None, source_row=len(exports) + 2,
        ))

    # "Other"-basket exports: one substitutable at 10-digit, one not (blocked), one with a matching import.
    if _OTHER_CODES:
        oc = _OTHER_CODES[0]  # 73269086
        # add a couple of matching imports so the 10-digit path has duty to claim against
        for j in range(2):
            ev = _money(Decimal("120") * 800)
            imp = ImportLine(
                entry_number=f"APX-{8000 + j:07d}", line_number=1, importer_id=IMPORTER_EIN,
                hts10=oc + "35", description=REF.description(oc), import_date=as_of - timedelta(days=400),
                entry_date=as_of - timedelta(days=399), quantity=800, unit_of_measure="No.",
                entered_value=ev, charges=_charges_for(oc, ev, add_232=True, add_ieepa=False),
                country_of_origin="CN", liquidated=True, source_row=len(imports) + 2)
            imports.append(imp)
        exports.append(ExportLine(reference=_new_ref(), hts10=oc + "35", description=REF.description(oc),
            export_date=as_of - timedelta(days=120), quantity=600, unit_of_measure="No.",
            value_per_unit=Decimal("120"), has_export_proof=True, source_row=len(exports) + 2))  # 10-digit OK
        exports.append(ExportLine(reference=_new_ref(), hts10=oc + "88", description=REF.description(oc),
            export_date=as_of - timedelta(days=110), quantity=300, unit_of_measure="No.",
            value_per_unit=Decimal("120"), has_export_proof=True, source_row=len(exports) + 2))  # blocked

    # A few exports with NO matching import subheading (NO_HTS_MATCH).
    for _ in range(3):
        exports.append(ExportLine(reference=_new_ref(), hts10="6109100010", description="Cotton T-shirts (no import)",
            export_date=as_of - timedelta(days=200), quantity=500, unit_of_measure="No.",
            value_per_unit=Decimal("6"), has_export_proof=True, source_row=len(exports) + 2))

    rng.shuffle(imports)
    rng.shuffle(exports)
    dq = DataQualityReport(imports_parsed=len(imports), exports_parsed=len(exports))
    return Dataset(imports=imports, exports=exports, data_quality=dq, importer_id=IMPORTER_EIN)


# ─────────────────────────────────────────────────────────────────────────────
# CSV rendering — ACE/ITRAC-like import file + EEI/invoice-like export file
# ─────────────────────────────────────────────────────────────────────────────
_IMPORT_HEADER = [
    "entry_number", "line_number", "importer_id", "hts10", "description", "import_date", "entry_date",
    "quantity", "uom", "entered_value", "duty_base", "duty_301", "duty_232", "duty_ieepa", "mpf", "hmf",
    "ad_cvd", "excise", "country_of_origin", "liquidated",
]
_EXPORT_HEADER = [
    "reference", "hts10", "description", "export_date", "quantity", "uom", "value_per_unit", "action",
    "destination_country", "has_export_proof", "proof_kind", "recovered_value_per_unit",
    "direct_id_entry", "direct_id_line",
]


def write_csvs(dataset: Dataset, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    imp_path, exp_path = out / "imports.csv", out / "exports.csv"
    with imp_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_IMPORT_HEADER)
        for im in dataset.imports:
            c = im.charges
            w.writerow([
                im.entry_number, im.line_number, im.importer_id, im.hts10, im.description,
                im.import_date.isoformat(), (im.entry_date or im.import_date).isoformat(), im.quantity,
                im.unit_of_measure, im.entered_value,
                c.get(ChargeType.BASE_DUTY, ZERO), c.get(ChargeType.SECTION_301, ZERO),
                c.get(ChargeType.SECTION_232, ZERO), c.get(ChargeType.IEEPA, ZERO),
                c.get(ChargeType.MPF, ZERO), c.get(ChargeType.HMF, ZERO),
                c.get(ChargeType.AD_CVD, ZERO), c.get(ChargeType.EXCISE, ZERO),
                im.country_of_origin, "Y" if im.liquidated else "N",
            ])
    with exp_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_EXPORT_HEADER)
        for ex in dataset.exports:
            w.writerow([
                ex.reference, ex.hts10, ex.description, ex.export_date.isoformat(), ex.quantity,
                ex.unit_of_measure, ex.value_per_unit, ex.action.value, ex.destination_country,
                "Y" if ex.has_export_proof else "N", ex.proof_kind, ex.recovered_value_per_unit,
                ex.direct_id_entry or "", ex.direct_id_line if ex.direct_id_line is not None else "",
            ])
    return imp_path, exp_path
