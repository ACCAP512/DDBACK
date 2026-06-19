"""Time-limit rules: the 5-year import->claim window and export/destruction placement.

Citations: 19 U.S.C. 1313(r)(1), 1313(j)(1)-(2); 19 CFR 190.51(e)(1). RESEARCH Q4. Assumption A-09.

The clock starts at the *import (importation) date* of the designated line and ends at the
*claim-filing date*. The export/destruction must fall after import, before the claim, and within the
5-year window. The narrow major-disaster / CBP-fault extension is NOT granted (conservative, A-09).
"""

from __future__ import annotations

from datetime import date


def five_year_deadline(import_date: date) -> date:
    """Last day a complete claim may be filed: 5 years after the import date.

    Implemented as the day before the 5th anniversary is NOT how CBP states it — the statute says
    "not later than 5 years after the date...was imported", so the deadline is the 5th anniversary
    date inclusive. Leap-day imports (Feb 29) map to Feb 28 in non-leap target years."""
    y, m, d = import_date.year + 5, import_date.month, import_date.day
    try:
        return date(y, m, d)
    except ValueError:  # Feb 29 -> Feb 28
        return date(y, m, d - 1)


def within_claim_window(import_date: date, claim_date: date) -> bool:
    """True if a claim filed on ``claim_date`` is timely for an import on ``import_date`` (<= 5 yrs)."""
    return import_date <= claim_date <= five_year_deadline(import_date)


def export_placement_ok(import_date: date, export_date: date, claim_date: date) -> tuple[bool, str]:
    """Validate the full chain import -> export/destruction -> claim (A-09).

    Returns (ok, reason). Conservative: any ordering violation or out-of-window fails closed.
    """
    if export_date < import_date:
        return False, f"export {export_date} precedes import {import_date} — cannot designate"
    if export_date > claim_date:
        return False, f"export {export_date} is after the claim date {claim_date}"
    deadline = five_year_deadline(import_date)
    if export_date > deadline:
        return False, f"export {export_date} is beyond the 5-year window (deadline {deadline})"
    if claim_date > deadline:
        return False, f"claim {claim_date} is beyond the 5-year window (deadline {deadline})"
    return True, "import -> export -> claim all within the 5-year window (19 USC 1313(r); 190.51(e))"
