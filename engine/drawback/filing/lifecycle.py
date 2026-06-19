"""Layer 3 (stubbed): simulated claim lifecycle + projected payout timing (RESEARCH Q13).

Drives the status dashboard with SIMULATED status data behind a clean interface, so it becomes real the
moment a filing backend exists (DECISIONS D-009). Models the real CBP states and the Accelerated-Payment
vs. liquidation timing, including the 3-years-from-liquidation retention clock (A-18).

⚠️  SIMULATED — NOT CONNECTED TO CBP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass
class LifecycleStep:
    state: str
    status: str          # "complete" | "projected"
    on: str              # ISO date
    note: str


def _next_friday(d: date) -> date:
    return d + timedelta(days=(4 - d.weekday()) % 7)  # ACE liquidates weekly on Fridays (Q13)


def simulate_lifecycle(
    filing_date: date,
    *,
    accelerated_payment: bool,
    estimated_amount: Decimal,
    today: date | None = None,
) -> dict:
    """Project a claim's lifecycle from a filing date. ``today`` (default = filing_date) marks which
    steps are already complete vs. projected."""
    today = today or filing_date
    accepted = filing_date
    complete = filing_date + timedelta(days=1)              # DIS docs within 24h
    ap_paid = filing_date + timedelta(days=21)              # ~3 weeks after AP acceptance
    liquidation = _next_friday(filing_date + timedelta(days=365))  # ~1 yr; Friday liquidation
    post_liq_pay = liquidation + timedelta(days=21)         # no-AP refund ~3 wks after decision
    retention_until = date(liquidation.year + 3, liquidation.month, min(liquidation.day, 28))

    def step(state, on, note) -> LifecycleStep:
        return LifecycleStep(state, "complete" if on <= today else "projected", on.isoformat(), note)

    steps = [
        step("transmitted", filing_date, "Claim transmitted via ABI/ACE (application id DE)."),
        step("accepted", accepted, "ACE returned an immediate accept."),
        step("complete", complete, "Supporting docs (CBP 7553 / 349 / 350) uploaded to DIS within 24h."),
    ]
    if accelerated_payment:
        steps.append(step("accelerated_payment_paid", ap_paid,
                          f"Estimated drawback paid ~3 weeks after AP acceptance (≈ ${estimated_amount:,.2f}), "
                          "secured by a 1A bond (19 CFR 190.92). Provisional until liquidation."))
    steps.append(step("under_review", complete + timedelta(days=2),
                      "CBP verification (19 CFR Part 190 Subpart F); liquidation typically 1–3 years."))
    steps.append(step("liquidated", liquidation,
                      "Final computation; ACE liquidates weekly on Fridays. Starts the 3-yr record clock."))
    if accelerated_payment:
        steps.append(step("ap_true_up", liquidation,
                          "AP trued up at liquidation — repay any excess over the liquidated amount."))
    else:
        steps.append(step("paid", post_liq_pay, "Refund disbursed ~3 weeks after the liquidation decision."))

    current = next((s.state for s in reversed(steps) if s.status == "complete"), "transmitted")
    return {
        "simulated": True,
        "banner": "SIMULATED — not connected to CBP. Projected dates illustrate timing only.",
        "filing_date": filing_date.isoformat(),
        "accelerated_payment": accelerated_payment,
        "current_state": current,
        "estimated_amount": float(round(estimated_amount, 2)),
        "projected_first_payment": (ap_paid if accelerated_payment else post_liq_pay).isoformat(),
        "retention_deadline": retention_until.isoformat(),
        "steps": [s.__dict__ for s in steps],
    }


def portfolio_ledger(claims_meta: list[dict], today: date) -> dict:
    """A running ledger of accruing recovery across simulated claims (status dashboard)."""
    total_filed = sum(Decimal(str(c.get("amount", 0))) for c in claims_meta)
    paid = sum(Decimal(str(c.get("amount", 0))) for c in claims_meta if c.get("paid"))
    return {
        "simulated": True,
        "as_of": today.isoformat(),
        "claims": len(claims_meta),
        "total_filed": float(round(total_filed, 2)),
        "received": float(round(paid, 2)),
        "in_flight": float(round(total_filed - paid, 2)),
    }
