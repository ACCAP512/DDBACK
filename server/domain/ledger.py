"""The designation ledger — the make-or-break correctness control (BUILD_PLAN §3, M1).

For each ``ImportEntryLine`` the ledger expresses, summed across **all** claims over **all** time:

    available_qty  →  designated_qty (Σ over every designation)  →  remaining_qty
    available_duty →  designated_duty                            →  remaining_duty

and the service **raises** :class:`OverDesignationError` if persisting a new set of designations
would push any import line's (or export line's) cumulative designated quantity past what was imported
(exported). That makes double-designation — claiming drawback twice against the same duty, 19 U.S.C.
1313(v) — *structurally impossible to persist*, not merely warned. It extends the engine's
within-estimate reconciliation invariant to the persistent, cross-claim, cross-time layer.

Conservation is enforced on **quantity** (the fundamental scarce resource: each imported unit may be
designated at most once). Because the eligible per-unit duty is constant for a given import line,
quantity conservation implies duty conservation; the duty figures above are the reporting view.

The check is computed from natural keys WITHOUT writing anything, so a violation leaves the session
clean for the caller to roll back.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.db.models import Designation, ExportLine, ImportEntryLine

ImportKey = Tuple[str, int]  # (entry_number, line_no)


# ─────────────────────────────────────────────────────────────────────────────
# Violations / error
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CapacityViolation:
    kind: str            # "import" | "export"
    key: str             # human label: "ENTRY/LINE" or the export reference
    available: int       # the line's imported/exported quantity
    already_designated: int   # Σ over all OTHER persisted designations
    proposed: int        # what this new persist would add

    @property
    def would_total(self) -> int:
        return self.already_designated + self.proposed

    def describe(self) -> str:
        return (f"{self.kind} {self.key}: {self.already_designated} already designated + "
                f"{self.proposed} proposed = {self.would_total} > {self.available} available")


class OverDesignationError(Exception):
    """Raised when a persist would over-designate one or more lines across claims/time (1313(v))."""

    def __init__(self, violations: List[CapacityViolation]):
        self.violations = list(violations)
        super().__init__(
            "designation would exceed available quantity (double-drawback, 19 U.S.C. 1313(v)): "
            + "; ".join(v.describe() for v in self.violations)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cross-claim designated totals (the "Σ over all claims" half of the ledger)
# ─────────────────────────────────────────────────────────────────────────────
def designated_qty_by_import_key(
    session: Session, client_id: str, keys: Optional[Iterable[ImportKey]] = None
) -> Dict[ImportKey, int]:
    """Σ designated quantity per import line (across every claim), keyed by (entry_number, line_no)."""
    rows = session.execute(
        select(
            ImportEntryLine.entry_number,
            ImportEntryLine.line_no,
            func.coalesce(func.sum(Designation.quantity), 0),
        )
        .join(Designation, Designation.import_entry_line_id == ImportEntryLine.id)
        .where(ImportEntryLine.client_id == client_id)
        .group_by(ImportEntryLine.entry_number, ImportEntryLine.line_no)
    ).all()
    out = {(en, ln): int(total) for en, ln, total in rows}
    if keys is not None:
        wanted: Set[ImportKey] = set(keys)
        out = {k: v for k, v in out.items() if k in wanted}
    return out


def designated_qty_by_export_ref(
    session: Session, client_id: str, refs: Optional[Iterable[str]] = None
) -> Dict[str, int]:
    """Σ designated quantity per export line (across every claim), keyed by reference."""
    rows = session.execute(
        select(ExportLine.reference, func.coalesce(func.sum(Designation.quantity), 0))
        .join(Designation, Designation.export_line_id == ExportLine.id)
        .where(ExportLine.client_id == client_id)
        .group_by(ExportLine.reference)
    ).all()
    out = {ref: int(total) for ref, total in rows}
    if refs is not None:
        wanted = set(refs)
        out = {k: v for k, v in out.items() if k in wanted}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The conservation invariant (raises)
# ─────────────────────────────────────────────────────────────────────────────
def assert_capacity_available(
    session: Session,
    *,
    client_id: str,
    import_proposed: Dict[ImportKey, int],
    import_capacity: Dict[ImportKey, int],
    export_proposed: Dict[str, int],
    export_capacity: Dict[str, int],
) -> None:
    """Raise :class:`OverDesignationError` if the proposed designations, **added to everything already
    designated across all claims**, would exceed any import or export line's available quantity.

    ``*_capacity`` is the line's imported/exported quantity (the true scarce amount). Computes nothing
    persistent — safe to call before writing; on raise the caller rolls back.
    """
    import_existing = designated_qty_by_import_key(session, client_id, import_proposed.keys())
    export_existing = designated_qty_by_export_ref(session, client_id, export_proposed.keys())

    violations: List[CapacityViolation] = []
    for key, proposed in import_proposed.items():
        available = import_capacity[key]
        already = import_existing.get(key, 0)
        if already + proposed > available:
            violations.append(
                CapacityViolation("import", f"{key[0]}/{key[1]}", available, already, proposed))
    for ref, proposed in export_proposed.items():
        available = export_capacity[ref]
        already = export_existing.get(ref, 0)
        if already + proposed > available:
            violations.append(CapacityViolation("export", ref, available, already, proposed))

    if violations:
        raise OverDesignationError(violations)


# ─────────────────────────────────────────────────────────────────────────────
# The per-line ledger view (available → designated → remaining; qty + duty)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LineLedger:
    import_entry_line_id: str
    entry_number: str
    line_no: int
    available_qty: int
    designated_qty: int
    remaining_qty: int
    per_unit_duty: Optional[Decimal]
    available_duty: Optional[Decimal]
    designated_duty: Optional[Decimal]
    remaining_duty: Optional[Decimal]


def import_line_ledger(session: Session, line: ImportEntryLine) -> LineLedger:
    """The ``available → designated → remaining`` view for one import line (qty + duty)."""
    designated = int(
        session.scalar(
            select(func.coalesce(func.sum(Designation.quantity), 0)).where(
                Designation.import_entry_line_id == line.id
            )
        )
        or 0
    )
    per_unit_duty: Optional[Decimal] = session.scalar(
        select(Designation.per_unit_designated_duty)
        .where(Designation.import_entry_line_id == line.id)
        .limit(1)
    )
    available_qty = line.quantity
    remaining_qty = available_qty - designated

    if per_unit_duty is not None:
        available_duty: Optional[Decimal] = per_unit_duty * Decimal(available_qty)
        designated_duty: Optional[Decimal] = per_unit_duty * Decimal(designated)
        remaining_duty: Optional[Decimal] = per_unit_duty * Decimal(remaining_qty)
    else:
        available_duty = designated_duty = remaining_duty = None

    return LineLedger(
        import_entry_line_id=line.id,
        entry_number=line.entry_number,
        line_no=line.line_no,
        available_qty=available_qty,
        designated_qty=designated,
        remaining_qty=remaining_qty,
        per_unit_duty=per_unit_duty,
        available_duty=available_duty,
        designated_duty=designated_duty,
        remaining_duty=remaining_duty,
    )
