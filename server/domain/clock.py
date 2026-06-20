"""The 5-year expiring-value clock (BUILD_PLAN §5, M3 — the cockpit's "use it or lose it" rollup).

Drawback is filed-or-lost: a complete claim must be filed **within 5 years of the import date**
(19 U.S.C. 1313(r)(1); 19 CFR 190.51(e)(1); ASSUMPTION A-09). Duty paid on import lines whose 5-year
window closes before they are designated to a claim is **abandoned**. This module surfaces that
at-risk value so the broker acts before the clock runs out — the single most product-defining number
on the work-queue home.

Correctness is anchored on the engine, not re-derived:

* the **deadline** reuses :func:`drawback.rules.time_windows.five_year_deadline` — the *same* date math
  the engine uses to decide eligibility, so the cockpit clock and the estimate never disagree;
* the **eligible duty** reuses the dated :mod:`drawback.config.tariff_eligibility` config — only
  drawback-eligible charge layers count toward at-risk value (§232/AD-CVD/IEEPA are excluded), and an
  unknown charge type defaults to ineligible (conservative).

The at-risk figure is the **eligible duty paid on the still-undesignated units** — the *ceiling* that
expires if the line is never claimed (the realized recovery, once matched to an export, is ≤ this).
Framed as a ceiling, it never overstates recovery, consistent with the glass-box / VERIFIED-only ethos.

Tenant isolation is structural: every query below runs on the request's scoped session, so the
``WHERE tenant_id = …`` predicate is injected automatically (``server.db.scoping``).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Mapping, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from drawback.config import tariff_eligibility as cfg
from drawback.models import ChargeType
from drawback.rules.time_windows import five_year_deadline

from server.db.models import Designation, ImportEntryLine

_CENTS = Decimal("0.01")


def _to_cents(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def eligible_duty_paid(charges: Mapping[str, object]) -> Decimal:
    """Σ of the import line's **drawback-eligible** charges, per the dated engine config.

    ``charges`` is the persisted ``{charge_type_value: amount}`` map. A key that is not a known
    :class:`~drawback.models.ChargeType`, or a known-but-ineligible one (§232, AD/CVD, IEEPA, …), is
    excluded — exactly the engine's eligibility decision, so this is the line's eligible duty pool.
    """
    total = Decimal("0")
    for key, amount in charges.items():
        try:
            charge = ChargeType(key)
        except ValueError:
            continue  # unknown charge type → conservatively ineligible
        if cfg.is_eligible(charge):
            total += Decimal(str(amount))
    return total


# ─────────────────────────────────────────────────────────────────────────────
# Urgency buckets (by days until the 5-year deadline)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class _Bucket:
    key: str
    label: str
    lo: Optional[int]  # inclusive lower bound on days_remaining (None = -∞)
    hi: Optional[int]  # inclusive upper bound on days_remaining (None = +∞)

    def contains(self, days: int) -> bool:
        return (self.lo is None or days >= self.lo) and (self.hi is None or days <= self.hi)


# Ordered most-urgent → least. "expired" is past the deadline (value already abandoned unless the
# claim was filed in time); the rest count down to it.
BUCKETS: List[_Bucket] = [
    _Bucket("expired", "Past deadline", None, -1),
    _Bucket("lte_90", "≤ 90 days", 0, 90),
    _Bucket("lte_180", "91–180 days", 91, 180),
    _Bucket("lte_365", "181–365 days", 181, 365),
    _Bucket("gt_365", "> 1 year", 366, None),
]


def _bucket_for(days_remaining: int) -> _Bucket:
    for b in BUCKETS:
        if b.contains(days_remaining):
            return b
    return BUCKETS[-1]  # unreachable (buckets cover ℤ), but fail safe


# ─────────────────────────────────────────────────────────────────────────────
# Per-line and rolled-up views
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LineClock:
    import_entry_line_id: str
    client_id: str
    entry_number: str
    line_no: int
    hts10: str
    import_date: date
    deadline: date
    days_remaining: int
    bucket: str
    quantity: int
    designated_qty: int
    remaining_qty: int
    eligible_duty_paid: Decimal     # whole-line eligible duty pool
    at_risk_duty: Decimal           # eligible duty on the undesignated units (the expiring ceiling)


@dataclass(frozen=True)
class BucketSummary:
    key: str
    label: str
    lines: int
    remaining_units: int
    at_risk_duty: Decimal


@dataclass(frozen=True)
class ExpiringValueRollup:
    as_of: date
    total_lines: int
    total_at_risk_duty: Decimal
    buckets: List[BucketSummary]
    soonest: List[LineClock]        # the most-urgent undesignated lines, deadline-ascending


def _designated_qty_by_line(session: Session) -> Dict[str, int]:
    """{import_entry_line_id: Σ designated quantity across all claims} for the scoped tenant."""
    rows = session.execute(
        select(
            Designation.import_entry_line_id,
            func.coalesce(func.sum(Designation.quantity), 0),
        ).group_by(Designation.import_entry_line_id)
    ).all()
    return {line_id: int(total) for line_id, total in rows}


def line_clock(line: ImportEntryLine, designated_qty: int, as_of: date) -> LineClock:
    """The 5-year-clock view for one import line given its Σ-designated quantity."""
    deadline = five_year_deadline(line.import_date)
    remaining_qty = max(0, line.quantity - designated_qty)
    pool = eligible_duty_paid(line.charges or {})
    if line.quantity > 0 and remaining_qty > 0:
        at_risk = _to_cents(pool * Decimal(remaining_qty) / Decimal(line.quantity))
    else:
        at_risk = Decimal("0.00")
    days = (deadline - as_of).days
    return LineClock(
        import_entry_line_id=line.id,
        client_id=line.client_id,
        entry_number=line.entry_number,
        line_no=line.line_no,
        hts10=line.hts10,
        import_date=line.import_date,
        deadline=deadline,
        days_remaining=days,
        bucket=_bucket_for(days).key,
        quantity=line.quantity,
        designated_qty=designated_qty,
        remaining_qty=remaining_qty,
        eligible_duty_paid=_to_cents(pool),
        at_risk_duty=at_risk,
    )


def expiring_value(
    session: Session,
    *,
    as_of: Optional[date] = None,
    soonest_limit: int = 20,
) -> ExpiringValueRollup:
    """Roll up at-risk drawback value across the tenant's import lines by 5-year-clock urgency.

    Only lines with **undesignated** quantity contribute — a fully-designated line has nothing left to
    lose. The ``soonest`` list is the most-urgent undesignated lines (deadline-ascending) for the
    cockpit's "act now" panel. Computed live from the designation ledger so it reflects every claim.
    """
    as_of = as_of or date.today()
    designated = _designated_qty_by_line(session)

    by_bucket_lines: Dict[str, int] = {b.key: 0 for b in BUCKETS}
    by_bucket_units: Dict[str, int] = {b.key: 0 for b in BUCKETS}
    by_bucket_duty: Dict[str, Decimal] = {b.key: Decimal("0.00") for b in BUCKETS}
    total_lines = 0
    total_at_risk = Decimal("0.00")
    clocks: List[LineClock] = []

    # Stream import lines so memory stays bounded even on a large book of business.
    for line in session.scalars(select(ImportEntryLine)).yield_per(1000):
        lc = line_clock(line, designated.get(line.id, 0), as_of)
        if lc.remaining_qty <= 0:
            continue
        total_lines += 1
        total_at_risk += lc.at_risk_duty
        by_bucket_lines[lc.bucket] += 1
        by_bucket_units[lc.bucket] += lc.remaining_qty
        by_bucket_duty[lc.bucket] += lc.at_risk_duty
        clocks.append(lc)

    buckets = [
        BucketSummary(
            key=b.key,
            label=b.label,
            lines=by_bucket_lines[b.key],
            remaining_units=by_bucket_units[b.key],
            at_risk_duty=by_bucket_duty[b.key],
        )
        for b in BUCKETS
    ]
    soonest = sorted(clocks, key=lambda c: (c.deadline, -c.at_risk_duty))[:soonest_limit]
    return ExpiringValueRollup(
        as_of=as_of,
        total_lines=total_lines,
        total_at_risk_duty=total_at_risk,
        buckets=buckets,
        soonest=soonest,
    )
