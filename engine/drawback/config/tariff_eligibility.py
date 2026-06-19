"""Dated, centralized drawback-eligibility config (DECISIONS D-006; ASSUMPTIONS A-12/A-13).

This is the ONE place time-sensitive eligibility lives. Tariff-layer drawback eligibility is the
fastest-changing, most error-prone area in the domain (RESEARCH Q5/Q18), so it is isolated here,
stamped with an as-of date that the UI surfaces, and defaults UNKNOWN charge types to *ineligible*
(conservative — PRD §11).

⚠️  Re-verify against current CSMS messages and the CIT/Fed. Cir. dockets before this drives a real
    CBP filing. Litigation here moves fast; everything below is current to the AS_OF date.
"""

from __future__ import annotations

from datetime import date

from drawback.models import ChargeType

# Bump this string whenever the table below changes; it is recorded in every Estimate.
VERSION = "2026-06-19.1"
AS_OF: date = date(2026, 6, 19)


# charge -> (is_drawback_eligible, authority, note)
_ELIGIBILITY: dict[ChargeType, tuple[bool, str, str]] = {
    ChargeType.BASE_DUTY: (
        True, "19 CFR 190.3(a)",
        "Ordinary Ch. 1-97 customs duty — drawback-eligible.",
    ),
    ChargeType.SECTION_301: (
        True, "19 CFR 190.3 (not excluded); CBP CSMS #18-000419",
        "USTR China tariffs — drawback-eligible; the largest reliably-eligible special layer.",
    ),
    ChargeType.MPF: (
        True, "19 CFR 190.3(a); Texport Oil v. United States, 185 F.3d 1291 (Fed. Cir. 1999)",
        "Merchandise Processing Fee (acct 499) — drawback-eligible.",
    ),
    ChargeType.HMF: (
        True, "19 CFR 190.3(a); Pub. L. 108-429 §1557 (2004)",
        "Harbor Maintenance Fee (acct 501) — eligible since the 2004 amendment reversed Texport's HMF holding.",
    ),
    ChargeType.EXCISE: (
        True, "19 CFR 190.3(a); NAM v. Treasury (Fed. Cir. 2021)",
        "Federal excise attaching on importation — 99% eligible; the invalidated substitution cap is NOT applied (A-07).",
    ),
    ChargeType.SECTION_232: (
        False, "Presidential Proclamations 9704/9705 & Apr-2026 successor; Fed. Reg. 2026-06960; CSMS #18-000317",
        "Steel/aluminum/copper national-security tariffs — 'no drawback shall be available.' "
        "A narrow derivative-manufacturing carve-out exists but is excluded by default (A-12).",
    ),
    ChargeType.IEEPA: (
        False, "Trump v. V.O.S. Selections, 605 U.S. ___ (2026-02-20); CBP CAPE process (2026-04-20)",
        "Struck down by SCOTUS; refunded via CAPE, NOT drawback (A-13). Contributes $0 to the drawback pool.",
    ),
    ChargeType.SECTION_122: (
        False, "Trade Act §122; CIT Slip Op. 26-47 (2026-05-07, on appeal)",
        "Balance-of-payments surcharge — struck down, on appeal, ≤150-day statutory life, no drawback guidance. "
        "Excluded as uncertain (conservative).",
    ),
    ChargeType.AD_CVD: (
        False, "19 U.S.C. 1677h; 19 CFR 190.3(b)",
        "Antidumping/countervailing duties 'shall not be treated as regular customs duties' — not drawback-eligible.",
    ),
}


def is_eligible(charge: ChargeType) -> bool:
    """True only if the charge is drawback-eligible as of AS_OF. Unknown -> False (conservative)."""
    entry = _ELIGIBILITY.get(charge)
    return bool(entry and entry[0])


def authority(charge: ChargeType) -> str:
    entry = _ELIGIBILITY.get(charge)
    return entry[1] if entry else "no authority on record — defaulted ineligible (conservative)"


def note(charge: ChargeType) -> str:
    entry = _ELIGIBILITY.get(charge)
    return entry[2] if entry else "Unknown charge type; excluded from the headline pending review."


def eligible_charges() -> set[ChargeType]:
    return {c for c, (ok, _a, _n) in _ELIGIBILITY.items() if ok}


def ineligible_charges() -> set[ChargeType]:
    return {c for c, (ok, _a, _n) in _ELIGIBILITY.items() if not ok}


# IEEPA gets its own bucket: not drawback, but routed to a clearly-labeled CAPE track (A-13).
CAPE_TRACK_CHARGES: set[ChargeType] = {ChargeType.IEEPA}


def config_summary() -> dict:
    """Machine-readable snapshot for the API/UI banner (PRD §11 date-stamp)."""
    return {
        "version": VERSION,
        "as_of": AS_OF.isoformat(),
        "eligible": sorted(c.value for c in eligible_charges()),
        "ineligible": sorted(c.value for c in ineligible_charges()),
        "rows": [
            {"charge": c.value, "eligible": ok, "authority": a, "note": n}
            for c, (ok, a, n) in _ELIGIBILITY.items()
        ],
    }
