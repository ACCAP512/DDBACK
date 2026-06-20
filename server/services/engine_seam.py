"""The engine seam (M0).

Two responsibilities, kept separate:

1. :func:`run_estimate` — run the engine's public pipeline on a ``Dataset`` and return its objects
   unchanged (``build_estimate`` then ``defensibility.harden``). No behavior change vs the existing
   ``api/main.py`` call site; this just moves the call server-side.
2. :func:`persist_estimate` — translate the engine's ``Estimate`` (+ the ``Dataset`` it came from)
   into persisted rows: the import/export lines, a ``Claim``, and one ``Designation`` per matched
   pair, plus an ``AuditEvent``. This is the round-trip the M0 gate requires.

The M1 milestone layers the **designation ledger** (across-time ``Σ designated ≤ available``) on top
of :func:`persist_estimate`; M0 establishes the faithful persistence it will guard.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from drawback.defensibility import DefensibilityResult, harden
from drawback.estimate import build_estimate
from drawback.models import Dataset, Estimate, ImportLine, ExportLine as EngineExportLine
from drawback.serialize import to_jsonable

from server.db import models as m
from server.domain.enums import ClaimMode, ClaimStatus


@dataclass
class EstimateRun:
    """The engine's outputs for one dataset, carried together for persistence."""

    estimate: Estimate
    defensibility: DefensibilityResult


def run_estimate(dataset: Dataset, claim_date: Optional[date] = None) -> EstimateRun:
    """Run the engine's public pipeline. ``harden(strict=True)`` RAISES on any reconciliation
    violation — an indefensible number must fail loudly, never persist silently."""
    estimate = build_estimate(dataset, claim_date)
    defensibility = harden(estimate, strict=True)
    return EstimateRun(estimate=estimate, defensibility=defensibility)


def _charges_to_json(line: ImportLine) -> dict:
    """{ChargeType.value: exact decimal string} — lossless, JSON-safe."""
    return {ctype.value: str(amount) for ctype, amount in line.charges.items()}


def persist_estimate(
    session: Session,
    *,
    program: m.Program,
    dataset: Dataset,
    run: EstimateRun,
    period: Optional[str] = None,
    mode: ClaimMode = ClaimMode.retroactive,
) -> m.Claim:
    """Persist ``dataset`` + ``run`` as ImportEntryLines + ExportLines + a Claim + Designations.

    Returns the persisted (flushed) ``Claim``. The caller owns the transaction (commit/rollback).
    """
    client = program.client
    tenant_id = client.tenant_id

    # 1) Import/export lines, keyed so designations can link to the persisted rows.
    import_by_key: dict[tuple[str, int], m.ImportEntryLine] = {}
    for im in dataset.imports:
        row = m.ImportEntryLine(
            tenant_id=tenant_id,
            client_id=client.id,
            entry_number=im.entry_number,
            line_no=im.line_number,
            hts10=im.hts10,
            import_date=im.import_date,
            quantity=im.quantity,
            uom=im.unit_of_measure,
            entered_value=im.entered_value,
            charges=_charges_to_json(im),
            liquidated=im.liquidated,
        )
        session.add(row)
        import_by_key[(im.entry_number, im.line_number)] = row

    export_by_ref: dict[str, m.ExportLine] = {}
    for ex in dataset.exports:
        row = m.ExportLine(
            tenant_id=tenant_id,
            client_id=client.id,
            reference=ex.reference,
            hts10=ex.hts10,
            export_date=ex.export_date,
            quantity=ex.quantity,
            uom=ex.unit_of_measure,
            value_per_unit=ex.value_per_unit,
            has_export_proof=ex.has_export_proof,
            itn=ex.reference if _looks_like_itn(ex) else None,
            direct_id_entry=ex.direct_id_entry,
            direct_id_line=ex.direct_id_line,
        )
        session.add(row)
        export_by_ref[ex.reference] = row

    # 2) The Claim — the engine's headline/defensible figures become the ledger's tracked amounts.
    est = run.estimate
    claim = m.Claim(
        program_id=program.id,
        period=period,
        mode=mode,
        status=ClaimStatus.draft,
        estimated_refund=est.headline_point,
        defensible_refund=run.defensibility.defensible_headline,
        tariff_config_version=est.tariff_config_version,
        as_of=est.as_of,
    )
    session.add(claim)
    session.flush()  # assign claim.id so the AuditEvent below can reference it

    # 3) One Designation per matched pair, linked to its persisted import & export lines.
    for pair in est.matched_pairs:
        import_row = import_by_key.get((pair.import_entry, pair.import_line_no))
        export_row = export_by_ref.get(pair.export_reference)
        if import_row is None or export_row is None:
            # A pair must reference lines present in the dataset; a miss means a translation bug.
            raise ValueError(
                f"designation references a line not in the dataset: "
                f"import={pair.import_entry}/{pair.import_line_no} export={pair.export_reference}"
            )
        session.add(
            m.Designation(
                tenant_id=tenant_id,
                claim=claim,
                import_line=import_row,
                export_line=export_row,
                quantity=pair.quantity,
                provision=pair.provision.value,
                per_unit_recovery=pair.per_unit_recovery,
                recovery=pair.recovery,
                recovery_low=pair.recovery_low,
                confidence=pair.confidence.value,
                in_headline=pair.in_headline,
                trace=to_jsonable(pair.trace),
            )
        )

    # 4) Audit the creation (M1 expands audit to every state change).
    session.add(
        m.AuditEvent(
            tenant_id=tenant_id,
            action="claim.created",
            target_type="claim",
            target_id=claim.id,
            detail={
                "estimated_refund": str(est.headline_point),
                "defensible_refund": str(run.defensibility.defensible_headline),
                "designations": len(est.matched_pairs),
                "tariff_config_version": est.tariff_config_version,
            },
        )
    )

    session.flush()  # assign PKs / resolve relationships without committing
    return claim


def _looks_like_itn(ex: EngineExportLine) -> bool:
    """AES filings carry an Internal Transaction Number as their reference (proof_kind 'aes_itn')."""
    return getattr(ex, "proof_kind", "") == "aes_itn"
