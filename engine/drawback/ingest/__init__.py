"""Real-format ingestion layer for the drawback engine.

Pipeline:  parse NetSuite commercial spine  +  parse customs overlay  ->  JOIN  ->  validate
->  ``Dataset`` (the engine's input contract).

NetSuite holds the COMMERCIAL transaction (item / qty / value / dates / parties) but not the duty;
the duty comes from the broker / ACE entry summary and the export-proof from AES/EEI. So the layer
fuses a NetSuite commercial spine to a customs overlay (``ingest.join``) to build the engine's
``ImportLine`` / ``ExportLine``.

Two split levels of failure (matching the engine's philosophy):
  * DATA-QUALITY issues (recoverable: a dropped row, a qty discrepancy, a missing AES match) go to
    the ``DataQualityReport`` and the pipeline keeps going — the produced estimate is just smaller.
  * HARD SCHEMA breaks (the produced lines violate the engine input contract: non-10-digit HTS,
    non-positive qty, missing required field, wrong type) raise ``IngestionError`` and FAIL LOUDLY,
    because feeding the engine malformed lines would silently corrupt a money number.

Public entry point: ``ingest_dataset(netsuite_dir, customs_dir) -> Dataset``.

NO network, stdlib-only core. The live NetSuite seam is ``ingest.client.NetSuiteClient``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List

from drawback.models import (
    ChargeType, Dataset, DataQualityReport, ExportLine, ImportLine,
)
from drawback.rules.hts import is_valid_hts10
from drawback.ingest import customs as _customs
from drawback.ingest import join as _join
from drawback.ingest.client import NetSuiteClient, StubbedNetSuiteClient

__all__ = [
    "ingest_dataset",
    "ingest_from_client",
    "IngestionError",
    "StubbedNetSuiteClient",
    "NetSuiteClient",
]


class IngestionError(Exception):
    """Raised on a HARD schema mismatch — the produced lines would violate the engine input
    contract. Recoverable data-quality problems never raise; they go to the DataQualityReport."""


def ingest_dataset(netsuite_dir, customs_dir, *, strict: bool = True) -> Dataset:
    """Parse the NetSuite export dir + the customs overlay dir, join them, validate, and return a
    ``Dataset`` ready for ``drawback.estimate.build_estimate``.

    ``netsuite_dir`` holds the NetSuite saved-search / SuiteQL exports (import + export spines);
    ``customs_dir`` holds the 7501/ACE entry-summary export and the AES/EEI export-proof export.
    The NetSuite read goes through the stubbed (fixture-mode) client so the live seam is exercised.
    """
    client = StubbedNetSuiteClient(netsuite_dir)
    return ingest_from_client(client, customs_dir, strict=strict)


def ingest_from_client(client: NetSuiteClient, customs_dir, *, strict: bool = True) -> Dataset:
    """Same pipeline as ``ingest_dataset`` but with an injected NetSuite client (the seam where a
    live SuiteQL/SuiteTalk client would replace the stub)."""
    report = DataQualityReport()

    # 1) commercial spine (NetSuite) — via the client seam
    commercial_imports = client.fetch_imports(report)
    commercial_exports = client.fetch_exports(report)

    # 2) customs overlay — duty (7501/ACE) + export proof (AES/EEI)
    entry_lines = _customs.parse_entry_dir(customs_dir, report)
    aes_lines = _customs.parse_aes_dir(customs_dir, report)

    # 3) JOIN commercial <-> customs -> engine lines
    imports = _join.join_imports(commercial_imports, entry_lines, report)
    exports = _join.join_exports(commercial_exports, aes_lines, report)

    # 4) VALIDATE against the engine input contract (hard breaks raise; data issues already reported)
    _validate_imports(imports, report, strict)
    _validate_exports(exports, report, strict)

    report.imports_parsed = len(imports)
    report.exports_parsed = len(exports)

    importer_id = _resolve_importer_id(imports)
    return Dataset(imports=imports, exports=exports, data_quality=report, importer_id=importer_id)


# ─────────────────────────────────────────────────────────────────────────────
# Contract validation
# ─────────────────────────────────────────────────────────────────────────────
def _validate_imports(imports: List[ImportLine], report: DataQualityReport, strict: bool) -> None:
    problems: List[str] = []
    for im in imports:
        where = "import entry %s line %s" % (im.entry_number, im.line_number)
        if not isinstance(im.entry_number, str) or not im.entry_number:
            problems.append("%s: missing/invalid entry_number" % where)
        if not isinstance(im.line_number, int):
            problems.append("%s: line_number is not int" % where)
        if not is_valid_hts10(im.hts10):
            problems.append("%s: hts10 %r is not 10 digits" % (where, im.hts10))
        if not isinstance(im.quantity, int) or im.quantity <= 0:
            problems.append("%s: quantity %r is not a positive int" % (where, im.quantity))
        if not isinstance(im.entered_value, Decimal):
            problems.append("%s: entered_value is not Decimal" % where)
        if not isinstance(im.import_date, date):
            problems.append("%s: import_date is not a date" % where)
        for ctype, amt in im.charges.items():
            if not isinstance(ctype, ChargeType):
                problems.append("%s: charge key %r is not a ChargeType" % (where, ctype))
            if not isinstance(amt, Decimal):
                problems.append("%s: charge %s amount is not Decimal" % (where, ctype))
    _raise_or_report(problems, report, strict, "imports")


def _validate_exports(exports: List[ExportLine], report: DataQualityReport, strict: bool) -> None:
    problems: List[str] = []
    for ex in exports:
        where = "export %s" % ex.reference
        if not isinstance(ex.reference, str) or not ex.reference:
            problems.append("%s: missing/invalid reference" % where)
        if not is_valid_hts10(ex.hts10):
            problems.append("%s: hts10 %r is not 10 digits" % (where, ex.hts10))
        if not isinstance(ex.quantity, int) or ex.quantity <= 0:
            problems.append("%s: quantity %r is not a positive int" % (where, ex.quantity))
        if not isinstance(ex.value_per_unit, Decimal):
            problems.append("%s: value_per_unit is not Decimal" % where)
        if not isinstance(ex.export_date, date):
            problems.append("%s: export_date is not a date" % where)
    _raise_or_report(problems, report, strict, "exports")


def _raise_or_report(problems: List[str], report: DataQualityReport, strict: bool, side: str) -> None:
    if not problems:
        return
    for p in problems:
        report.add("error", -1, side, p)
    if strict:
        head = problems[:12]
        more = "" if len(problems) <= 12 else "\n  ... and %d more" % (len(problems) - 12)
        raise IngestionError(
            "ingestion produced %d line(s) that violate the engine input contract (%s):\n  %s%s"
            % (len(problems), side, "\n  ".join(head), more)
        )


def _resolve_importer_id(imports: List[ImportLine]) -> str:
    for im in imports:
        if im.importer_id:
            return im.importer_id
    return ""
