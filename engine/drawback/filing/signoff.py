"""Licensed-filer sign-off gate (COMPLIANCE.md §4 P3; CBP HQ H350722, Jan 2026).

The ruling: the actual decision on a drawback claim "must be made by a duly licensed customs broker,"
who "must have a role in specifying" what an automated tool generates. So no CATAIR claim file is
treated as FINAL or submitted until a **lawful operator** — a licensed U.S. customs broker/attorney, or
an importer/exporter self-filing solely on its own account (the EULA field-of-use set) — affirmatively
accepts the matches, rules, and figures, recorded with name / role / timestamp. This makes the
determination THEIRS and keeps the unlicensed software vendor on the clean side of the customs-business
line. Stdlib-only; the API layer maps a request onto ``FilerAttestation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FilerRole(str, Enum):
    LICENSED_CUSTOMS_BROKER = "licensed_customs_broker"
    CUSTOMS_ATTORNEY = "customs_attorney"
    SELF_FILER_OWN_ACCOUNT = "self_filer_own_account"


# Roles that need a license/identifier on record (the broker/attorney; a self-filer files on own account).
_LICENSED_ROLES = {FilerRole.LICENSED_CUSTOMS_BROKER, FilerRole.CUSTOMS_ATTORNEY}

ATTESTATION_STATEMENT = (
    "I am the lawful filer of this drawback claim (a licensed U.S. customs broker or attorney, or the "
    "importer/exporter filing solely on its own account). I have independently reviewed the matched "
    "import↔export designations, the governing rules, and the computed amounts, and I accept "
    "responsibility for the determination and the filing. I understand this software is decision-support "
    "only — it does not transact customs business and does not file with CBP."
)


class SignoffError(ValueError):
    """Raised when an attestation is missing, incomplete, or from an unrecognized (non-lawful) role."""


@dataclass
class FilerAttestation:
    filer_name: str
    role: FilerRole
    attested_on: str               # ISO timestamp of the human attestation
    license_number: str = ""       # required for a licensed broker/attorney
    accepted_defensible: bool = False
    accepted_review_understood: bool = False
    statement: str = ATTESTATION_STATEMENT


def validate(att: FilerAttestation) -> list[str]:
    """Return a list of issues; empty means the attestation is sufficient to finalize a claim."""
    issues: list[str] = []
    if not att.filer_name or not att.filer_name.strip():
        issues.append("filer_name is required")
    if not isinstance(att.role, FilerRole):
        issues.append(f"role must be one of {[r.value for r in FilerRole]}")
    elif att.role in _LICENSED_ROLES and not att.license_number.strip():
        issues.append("license_number is required for a licensed customs broker or attorney")
    if not att.accepted_defensible:
        issues.append("the filer must affirmatively accept the figures (accepted_defensible must be true)")
    return issues


def record(att: FilerAttestation) -> dict:
    """Validate and return a sign-off record to attach to the claim/manifest. Raises on invalid."""
    issues = validate(att)
    if issues:
        raise SignoffError("; ".join(issues))
    return {
        "signed": True,
        "filer_name": att.filer_name.strip(),
        "role": att.role.value,
        "license_number": att.license_number.strip(),
        "attested_on": att.attested_on,
        "accepted_defensible": att.accepted_defensible,
        "accepted_review_understood": att.accepted_review_understood,
        "statement": att.statement,
    }
