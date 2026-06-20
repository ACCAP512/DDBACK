"""Portfolio cockpit routes — the work-queue home (BUILD_PLAN §5, M3).

``GET /api/portfolio/summary`` is the one call the home screen makes: the lifecycle histogram, the
triage lanes (with previews), the 5-year expiring-value clock, and per-client accrued $ — everything
to flip the tool from a calculator into a daily book-of-business cockpit. ``GET /api/portfolio/clock``
is the deeper expiring-value drill-down.

All reads run on the tenant-scoped session (isolation is automatic). The cockpit is a **staff** view:
it spans every client in the tenant, so the read-only ``client`` role is refused here — a client sees
only its own claims through the (scoped) claim routes, never the cross-client rollup.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from server.api.deps import get_scoped_db, require
from server.auth.context import Principal
from server.auth.rbac import Permission
from server.domain import clock as clock_domain
from server.domain import portfolio
from server.domain.enums import ClaimStatus, UserRole

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def staff_only(principal: Principal = Depends(require(Permission.CLAIMS_READ))) -> Principal:
    """CLAIMS_READ **and** not the client role — the cockpit aggregates across all clients."""
    if principal.role is UserRole.client:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "the portfolio cockpit is a staff view (cross-client)")
    return principal


# ── serialization (Decimal → exact string, dates → ISO) ───────────────────────
def _money(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else str(value)


def _dt(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _d(value: Optional[date]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _card_json(c: portfolio.ClaimCard) -> dict:
    return {
        "id": c.id,
        "client_id": c.client_id,
        "client_name": c.client_name,
        "program_id": c.program_id,
        "program_name": c.program_name,
        "drawback_type": c.drawback_type,
        "status": c.status,
        "mode": c.mode,
        "period": c.period,
        "estimated": _money(c.estimated),
        "defensible": _money(c.defensible),
        "actual": _money(c.actual),
        "gap": _money(c.gap),
        "signed": c.signed,
        "filed_at": _dt(c.filed_at),
        "liquidated_at": _dt(c.liquidated_at),
        "updated": _dt(c.updated),
    }


def _lane_json(ln: portfolio.Lane) -> dict:
    return {
        "key": ln.key,
        "label": ln.label,
        "hint": ln.hint,
        "count": ln.count,
        "total_defensible": _money(ln.total_defensible),
        "preview": [_card_json(c) for c in ln.preview],
    }


def _line_clock_json(lc: clock_domain.LineClock) -> dict:
    return {
        "import_entry_line_id": lc.import_entry_line_id,
        "client_id": lc.client_id,
        "entry_number": lc.entry_number,
        "line_no": lc.line_no,
        "hts10": lc.hts10,
        "import_date": _d(lc.import_date),
        "deadline": _d(lc.deadline),
        "days_remaining": lc.days_remaining,
        "bucket": lc.bucket,
        "quantity": lc.quantity,
        "designated_qty": lc.designated_qty,
        "remaining_qty": lc.remaining_qty,
        "eligible_duty_paid": _money(lc.eligible_duty_paid),
        "at_risk_duty": _money(lc.at_risk_duty),
    }


def _clock_json(roll: clock_domain.ExpiringValueRollup) -> dict:
    return {
        "as_of": _d(roll.as_of),
        "total_lines": roll.total_lines,
        "total_at_risk_duty": _money(roll.total_at_risk_duty),
        "buckets": [
            {
                "key": b.key,
                "label": b.label,
                "lines": b.lines,
                "remaining_units": b.remaining_units,
                "at_risk_duty": _money(b.at_risk_duty),
            }
            for b in roll.buckets
        ],
        "soonest": [_line_clock_json(lc) for lc in roll.soonest],
    }


def _accrued_json(a: portfolio.ClientAccrued) -> dict:
    return {
        "client_id": a.client_id,
        "client_name": a.client_name,
        "importer_id": a.importer_id,
        "claims_total": a.claims_total,
        "pipeline": _money(a.pipeline),
        "in_flight": _money(a.in_flight),
        "realized": _money(a.realized),
    }


# ── endpoints ─────────────────────────────────────────────────────────────────
@router.get("/summary")
def portfolio_summary(
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(staff_only),
) -> dict:
    """Everything the work-queue home renders, in one call."""
    by_status = portfolio.claims_by_status(db)
    lanes = portfolio.lanes(db)
    accrued = portfolio.per_client_accrued(db)
    roll = clock_domain.expiring_value(db, soonest_limit=10)

    active_claims = sum(n for s, n in by_status.items() if s != ClaimStatus.paid.value)
    totals = {
        "clients": len(accrued),
        "active_claims": active_claims,
        "at_risk_duty": _money(roll.total_at_risk_duty),
        "pipeline": _money(sum((a.pipeline for a in accrued), Decimal("0.00"))),
        "in_flight": _money(sum((a.in_flight for a in accrued), Decimal("0.00"))),
        "realized": _money(sum((a.realized for a in accrued), Decimal("0.00"))),
    }
    return {
        "as_of": _d(roll.as_of),
        "totals": totals,
        "by_status": by_status,
        "lanes": [_lane_json(ln) for ln in lanes],
        "clock": _clock_json(roll),
        "accrued": [_accrued_json(a) for a in accrued],
    }


@router.get("/clock")
def portfolio_clock(
    limit: int = Query(50, ge=1, le=500, description="how many soonest-expiring lines to return"),
    db: Session = Depends(get_scoped_db),
    principal: Principal = Depends(staff_only),
) -> dict:
    """The expiring-value drill-down: buckets + the ``limit`` most-urgent undesignated import lines."""
    return _clock_json(clock_domain.expiring_value(db, soonest_limit=limit))
