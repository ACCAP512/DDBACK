"""The commercial <-> customs JOIN: NetSuite spine fused with the broker/AES overlay,
producing the engine's ``ImportLine`` / ``ExportLine``.

IMPORT side
-----------
NetSuite holds the commercial receipt (item / qty / value / dates / vendor); the broker 7501 /
ACE entry summary holds the entry number + the duty. We join on the shared reference the broker
keys the entry to — the PO number or commercial-invoice number (``CommercialImport.join_ref`` ==
``CustomsEntryLine.join_ref``) — and produce one ``ImportLine`` carrying the duty from customs and
the descriptive/commercial context from NetSuite.

Real-world wrinkles handled (all surfaced to the ``DataQualityReport``):
  * MULTI-RECEIPT-TO-ONE-ENTRY: several NetSuite Item Receipts consolidated under a single 7501
    line (one entry covers a container with multiple receipts). The customs line is authoritative
    for duty; we attribute it once (to the entry line) and reconcile the summed commercial qty.
  * QUANTITY RECONCILIATION: commercial received qty vs. customs net qty. Mismatch beyond a small
    tolerance is flagged; the CUSTOMS quantity governs the ImportLine (it is what duty was assessed
    on and what the claim designates), the discrepancy is reported.
  * MISSING CUSTOMS: a NetSuite receipt with no matching entry line -> cannot be a drawback
    designated import (no duty, no entry number). Flagged and DROPPED (no fabricated entry).
  * ENTRY WITHOUT COMMERCIAL: a 7501 line with no NetSuite match -> still a valid designated import
    (the duty is real); kept, using the customs description, flagged "no commercial context".

EXPORT side
-----------
NetSuite holds the sale (SO / Item Fulfillment); AES/EEI holds the export proof (ITN) and the
destination of record. We join on the shipment / commercial-invoice reference. A match sets
``has_export_proof=True`` with the ITN (or B/L) as the proof token; no AES match -> the sale still
becomes an ``ExportLine`` but ``has_export_proof=False`` (the engine demotes it to "potential,
needs review", A-15) — we never invent proof.

The produced lines are validated against the engine input contract by ``ingest.__init__``.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from drawback.models import (
    DataQualityReport, ExportAction, ExportLine, ImportLine,
)
from drawback.rules.hts import normalize_hts
from drawback.ingest.customs import AesExportRecord, CustomsEntryLine
from drawback.ingest.records import CommercialExport, CommercialImport

# Quantity-reconciliation tolerance: commercial vs. customs net qty may differ slightly from
# rounding/packaging. Beyond this fraction we flag a real discrepancy. [GUESS] — see INGESTION.md.
_QTY_TOLERANCE = Decimal("0.02")


def _money(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _norm_ref(ref: str) -> str:
    """Canonicalize a join reference so 'PO-10481', 'po 10481', 'PO10481' all match."""
    return "".join(ch for ch in (ref or "").upper() if ch.isalnum())


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT JOIN
# ─────────────────────────────────────────────────────────────────────────────
def join_imports(
    commercial: List[CommercialImport],
    customs: List[CustomsEntryLine],
    report: DataQualityReport,
) -> List[ImportLine]:
    """Fuse NetSuite import receipts with 7501/ACE entry-summary lines -> ImportLine[].

    The customs entry line is the unit of a designated import (duty is assessed per entry line).
    Multiple commercial receipts may share one entry line's ``join_ref`` (multi-receipt-to-one-
    entry); they are grouped and reconciled against that single customs line.
    """
    commercial_by_ref: Dict[str, List[CommercialImport]] = defaultdict(list)
    for c in commercial:
        commercial_by_ref[_norm_ref(c.join_ref)].append(c)

    matched_commercial_refs = set()
    out: List[ImportLine] = []

    for ce in customs:
        ref_key = _norm_ref(ce.join_ref)
        receipts = commercial_by_ref.get(ref_key, [])
        if receipts:
            matched_commercial_refs.add(ref_key)

        # ── quantity reconciliation (multi-receipt aware) ──
        # The customs qty always governs the designated import (it is the duty basis); a commercial
        # vs. customs drift is never fatal — it is reported as "within tolerance" (rounding/packaging
        # noise) or as a real mismatch above _QTY_TOLERANCE. Either way: warning, never a drop.
        commercial_qty = sum(r.quantity for r in receipts)
        if receipts and commercial_qty != ce.quantity:
            denom = Decimal(ce.quantity) if ce.quantity else Decimal(1)
            drift = abs(Decimal(commercial_qty) - Decimal(ce.quantity)) / denom
            band = "within tolerance" if drift <= _QTY_TOLERANCE else "ABOVE tolerance"
            note = (
                "qty reconciliation (%s): NetSuite receipts total %d vs. 7501 net qty %d "
                "(entry %s line %d); customs qty governs the designated import"
                % (band, commercial_qty, ce.quantity, ce.entry_number, ce.line_number)
            )
            report.add("warning", ce.source_row, "quantity", note)
        if len(receipts) > 1:
            report.add("warning", ce.source_row, "join_ref",
                       "multi-receipt-to-one-entry: %d NetSuite receipts consolidated under "
                       "entry %s line %d (ref %s)"
                       % (len(receipts), ce.entry_number, ce.line_number, ce.join_ref))

        # ── descriptive context: prefer NetSuite description if present, else the 7501's ──
        description = ce.description
        if receipts and receipts[0].description:
            description = receipts[0].description
        if not receipts:
            report.add("warning", ce.source_row, "join_ref",
                       "entry %s line %d has no matching NetSuite receipt (ref %s) — kept with "
                       "customs-only context" % (ce.entry_number, ce.line_number, ce.join_ref))

        out.append(ImportLine(
            entry_number=ce.entry_number,
            line_number=ce.line_number,
            importer_id=ce.importer_of_record,
            hts10=ce.hts10,
            description=description,
            import_date=ce.import_date,
            quantity=ce.quantity,                       # customs qty governs (duty basis)
            unit_of_measure=ce.unit_of_measure,
            entered_value=ce.entered_value,
            charges=dict(ce.charges),
            country_of_origin=ce.country_of_origin,
            entry_date=ce.entry_date or ce.import_date,
            liquidated=ce.liquidated,
            source_row=ce.source_row,
        ))

    # ── missing-customs commercial receipts: real purchase, but no entry/duty -> cannot designate ──
    for key, receipts in commercial_by_ref.items():
        if key in matched_commercial_refs:
            continue
        for r in receipts:
            report.add("warning", r.source_row, "join_ref",
                       "NetSuite import receipt %s (item %s, ref %s) has no matching 7501/ACE entry "
                       "line — no duty to designate; dropped from import set"
                       % (r.tranid or r.internal_id, r.item, r.join_ref))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT JOIN
# ─────────────────────────────────────────────────────────────────────────────
def join_exports(
    commercial: List[CommercialExport],
    aes: List[AesExportRecord],
    report: DataQualityReport,
) -> List[ExportLine]:
    """Fuse NetSuite sales/fulfillments with AES/EEI proof -> ExportLine[].

    Match on the shipment / commercial-invoice reference. Matched -> ``has_export_proof=True`` with
    the ITN (or B/L) as the proof token and the AES country of ultimate destination. Unmatched ->
    the sale still becomes an ExportLine but ``has_export_proof=False`` (engine demotes it, A-15).
    """
    aes_by_ref: Dict[str, List[AesExportRecord]] = defaultdict(list)
    for a in aes:
        aes_by_ref[_norm_ref(a.join_ref)].append(a)

    used_aes = set()
    out: List[ExportLine] = []

    for ce in commercial:
        key = _norm_ref(ce.join_ref)
        candidates = [a for a in aes_by_ref.get(key, []) if id(a) not in used_aes]
        proof: Optional[AesExportRecord] = None
        if candidates:
            # Prefer the AES line whose HTS prefix matches the sale's item HTS hint when present;
            # otherwise take the first unused AES line on that reference.
            hint = normalize_hts(ce.hint_hts or "")
            chosen = None
            if hint:
                for a in candidates:
                    if a.hts10[:8] == hint[:8]:
                        chosen = a; break
            proof = chosen or candidates[0]
            used_aes.add(id(proof))

        # HTS for the export line: AES Schedule B/HTSUS is authoritative for the export
        # classification; fall back to the NetSuite item HTS hint if no AES match.
        hts10 = (proof.hts10 if proof else normalize_hts(ce.hint_hts or ""))
        if len(hts10) < 8:
            report.add("warning", ce.source_row, "hts10",
                       "NetSuite export %s (item %s, ref %s) has no AES classification and no usable "
                       "item HTS hint — export line will not match an import bucket"
                       % (ce.tranid or ce.internal_id, ce.item, ce.join_ref))
            # keep a placeholder so the row is visible; engine will mark NO_HTS_MATCH
            hts10 = hts10 or "0000000000"

        if proof is not None:
            reference = proof.itn or proof.bill_of_lading or ce.join_ref
            has_proof = bool(proof.itn or proof.bill_of_lading)
            proof_kind = "aes_itn" if proof.itn else ("bill_of_lading" if proof.bill_of_lading else "none")
            destination = proof.destination_country
            # value at port of export from AES if priced there, else the NetSuite sales rate
            vpu = proof.value_per_unit if proof.value_per_unit > 0 else ce.unit_price
            export_date = proof.export_date
        else:
            report.add("warning", ce.source_row, "has_export_proof",
                       "NetSuite export %s (ref %s) has no matching AES/EEI filing — no export proof; "
                       "engine will hold it as potential (needs review)"
                       % (ce.tranid or ce.internal_id, ce.join_ref))
            reference = ce.tranid or ce.join_ref
            has_proof = False
            proof_kind = "none"
            destination = ce.ship_country
            vpu = ce.unit_price
            export_date = ce.transaction_date

        out.append(ExportLine(
            reference=reference,
            hts10=hts10,
            description=ce.description or (proof.description if proof else ""),
            export_date=export_date,
            quantity=ce.quantity,
            unit_of_measure=ce.unit_of_measure,
            value_per_unit=_money(vpu),
            action=ExportAction.EXPORT,
            destination_country=destination,
            has_export_proof=has_proof,
            proof_kind=proof_kind,
            source_row=ce.source_row,
        ))

    # AES lines with no commercial match: proof exists but no sale in the spine -> can't place it.
    for key, recs in aes_by_ref.items():
        for a in recs:
            if id(a) not in used_aes:
                report.add("warning", a.source_row, "join_ref",
                           "AES/EEI line ITN %s (ref %s) has no matching NetSuite sale — export proof "
                           "with no commercial line; not used" % (a.itn or a.bill_of_lading, a.join_ref))
    return out
