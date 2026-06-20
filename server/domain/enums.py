"""Controlled vocabularies for the domain model.

Stored as portable ``VARCHAR + CHECK`` (non-native enum) so the DB rejects invalid states — the
claim status ledger in particular is correctness-critical. These Python enums are the single source
of truth; the service layer validates against them.
"""
from __future__ import annotations

from enum import Enum


class TenantKind(str, Enum):
    broker_firm = "broker_firm"      # a customs brokerage running many importers' books
    self_filer = "self_filer"        # an importer self-filing its own drawback


class UserRole(str, Enum):
    admin = "admin"
    preparer = "preparer"
    reviewer = "reviewer"
    signer = "signer"                # the licensed-filer sign-off role (gates finalizing a claim)
    client = "client"                # read-only, scoped to one Client


class DrawbackType(str, Enum):
    j1 = "j1"   # 1313(j)(1) unused merchandise, direct identification
    j2 = "j2"   # 1313(j)(2) unused merchandise, substitution
    a = "a"     # 1313(a) manufacturing, direct identification
    b = "b"     # 1313(b) manufacturing, substitution
    c = "c"     # 1313(c) rejected merchandise


class ClaimMode(str, Enum):
    retroactive = "retroactive"      # look-back over historical entries
    periodic = "periodic"            # accrual / ongoing


class ClaimStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    filed = "filed"
    under_review = "under_review"
    liquidated = "liquidated"
    paid = "paid"


class DocType(str, Enum):
    form_7501 = "form_7501"          # CBP entry summary
    bill_of_lading = "bill_of_lading"
    aes_eei = "aes_eei"              # AES/EEI export proof
    invoice = "invoice"
    form_7553 = "form_7553"          # notice of intent to export/destroy
    bom = "bom"                      # bill of materials (manufacturing)
    other = "other"


class DocStatus(str, Enum):
    uploaded = "uploaded"
    ocr_done = "ocr_done"
    matched = "matched"
    needs_review = "needs_review"    # extracted but not yet human-confirmed (default after OCR)
    confirmed = "confirmed"


class ChecklistStatus(str, Enum):
    pending = "pending"
    satisfied = "satisfied"
    not_applicable = "not_applicable"


class TaskKind(str, Enum):
    gap = "gap"                      # an unmet checklist/data requirement
    chase = "chase"                  # follow-up to obtain a missing document
    client_request = "client_request"
    review = "review"


class TaskStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"
