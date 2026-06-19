"""Canonical data models for the Drawback Engine.

PURE STANDARD LIBRARY (DECISIONS D-002). Money is ``decimal.Decimal`` (D-003 / A-16);
quantities are integer HTSUS units in the MVP (fractional-UOM support is a documented seam).

These types are the contract shared by the rules, matcher, parser, generator, estimate, and API
layers. They carry no business logic beyond trivial derived properties — the rules live in
``drawback.rules`` and ``drawback.matching`` so the legal logic stays in one auditable place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

CENTS = Decimal("0.01")
ZERO = Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# Charge types and drawback provisions
# ─────────────────────────────────────────────────────────────────────────────
class ChargeType(str, Enum):
    """A duty/tax/fee component on an import line. Eligibility is decided by
    ``config.tariff_eligibility`` (A-12), NOT by this enum — keep the two separate so the
    dated config is the single source of truth."""

    BASE_DUTY = "base_duty"          # ordinary Ch. 1-97 customs duty (eligible)
    SECTION_301 = "section_301"      # USTR China tariffs (eligible — CSMS #18-000419)
    SECTION_232 = "section_232"      # steel/aluminum/copper (NOT eligible)
    SECTION_122 = "section_122"      # balance-of-payments surcharge (excluded — uncertain)
    IEEPA = "ieepa"                  # 2025 reciprocal/fentanyl (struck down -> CAPE, not drawback)
    MPF = "mpf"                      # Merchandise Processing Fee, acct 499 (eligible)
    HMF = "hmf"                      # Harbor Maintenance Fee, acct 501 (eligible post-2004)
    AD_CVD = "ad_cvd"                # antidumping/countervailing (NOT eligible — 19 USC 1677h)
    EXCISE = "excise"               # federal excise attaching on importation (eligible, 99%)


class DrawbackProvision(str, Enum):
    """19 U.S.C. 1313 pathways. Value = CATAIR Appendix-A TFTEA provision code (RESEARCH Q17)."""

    J1_UNUSED_DIRECT = "58"          # 1313(j)(1) unused, direct identification
    J2_UNUSED_SUBSTITUTION = "59"    # 1313(j)(2) unused, substitution   <-- MVP primary
    A_MFG_DIRECT = "51"              # 1313(a) manufacturing, direct identification
    B_MFG_SUBSTITUTION = "52"        # 1313(b) manufacturing, substitution
    C_REJECTED = "53"                # 1313(c) rejected merchandise


class ExportAction(str, Enum):
    EXPORT = "export"
    DESTROY = "destroy"


class MatchBasis(str, Enum):
    DIRECT_IDENTIFICATION = "direct_identification"
    SUBSTITUTION_8_DIGIT = "substitution_8_digit"
    SUBSTITUTION_10_DIGIT = "substitution_10_digit_other_basket"  # A-02 fallback


class Confidence(str, Enum):
    """Drives the headline/potential partition (D-008)."""

    HIGH = "high"       # all [VERIFIED] assumptions, proof present, in window -> headline
    MEDIUM = "medium"   # relies on an [INFERRED] assumption -> potential (needs review)
    LOW = "low"         # missing proof / out-of-window / data issue -> blocked, needs review


class BlockedReason(str, Enum):
    MISSING_EXPORT_PROOF = "missing_export_proof"          # A-15
    OUT_OF_WINDOW = "out_of_window"                        # A-09
    INELIGIBLE_DUTY_ONLY = "ineligible_duty_only"          # only 232/IEEPA/122/AD-CVD present
    NO_HTS_MATCH = "no_hts_match"                          # no eligible import bucket for export
    NOT_LIQUIDATED = "not_liquidated"                      # A-14
    UNUSED_IMPORT_DUTY = "unused_import_duty"              # duty-paid units with no export to justify
    OTHER_BASKET_NO_MATCH = "other_basket_no_match"        # A-02: 8-digit "other" + no 10-digit match
    DATA_QUALITY = "data_quality"


# ─────────────────────────────────────────────────────────────────────────────
# Inputs
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ImportLine:
    """One CBP Form 7501 / ACE entry-summary line — a candidate *designated* import (RESEARCH Q14)."""

    entry_number: str                # blk 1, the join key
    line_number: int                 # col 31
    importer_id: str                 # blk 27 importer-of-record (IRS/EIN)
    hts10: str                       # col 33A, 10-digit (digits only, normalized by parser)
    description: str                 # col 32
    import_date: date                # blk 11 date of importation — starts the 5-yr clock (A-09)
    quantity: int                    # col 35 net qty in HTSUS units
    unit_of_measure: str             # col 35 UOM
    entered_value: Decimal           # col 36A — basis for ad valorem charges
    charges: dict[ChargeType, Decimal]  # col 38 / Other Fee Summary, split by component
    country_of_origin: str = "CN"    # blk 10
    entry_date: Optional[date] = None  # blk 7
    liquidated: bool = True          # A-14 — finally liquidated? unknown -> caller flags
    source_row: int = -1             # provenance back to the uploaded file row

    @property
    def hts8(self) -> str:
        return self.hts10[:8]

    def total_charges(self) -> Decimal:
        return sum(self.charges.values(), ZERO)


@dataclass
class ExportLine:
    """One export or destruction event — EEI/AES or B/L derived (RESEARCH Q15).

    For substitution the exported article need NOT be duty-paid (A-19); ``value_per_unit`` is the
    value at the U.S. port of export, used only to compute the lesser-of comparator (A-03)."""

    reference: str                   # invoice / BOL / AES ITN
    hts10: str                       # Schedule B or HTSUS, 10-digit normalized
    description: str
    export_date: date
    quantity: int
    unit_of_measure: str
    value_per_unit: Decimal          # value at port of export (per unit) — comparator input
    action: ExportAction = ExportAction.EXPORT
    destination_country: str = "US"  # ISO; "US" sentinel only for destruction
    has_export_proof: bool = True    # A-15 — is acceptable proof (B/L, ITN, 3rd-party destruction) present?
    proof_kind: str = "bill_of_lading"
    recovered_value_per_unit: Decimal = ZERO  # destruction: deduct recovered materials (190.71(d))
    # Optional explicit direct-identification link (A-08): the specific import lot this exported unit
    # was identified from. When set and the HTS10 matches, a (j)(1) arc (no lesser-of cap) is allowed.
    direct_id_entry: Optional[str] = None
    direct_id_line: Optional[int] = None
    source_row: int = -1

    @property
    def hts8(self) -> str:
        return self.hts10[:8]


@dataclass
class Dataset:
    """A tenant's import + export data plus the parser's data-quality findings."""

    imports: list[ImportLine]
    exports: list[ExportLine]
    data_quality: "DataQualityReport"
    importer_id: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Explainability — every claimed dollar carries one of these (PRD §4.3 hard requirement)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Trace:
    """The defensible basis for a matched pair's recovery. No number appears in any total
    without one of these (PRD §4.6)."""

    match_basis: MatchBasis
    provision: DrawbackProvision
    rule_citations: list[str]                     # e.g. ["19 CFR 190.32(b)(1)", "19 USC 1313(j)(2)"]
    assumption_ids: list[str]                     # e.g. ["A-01", "A-03", "A-10"]
    computation_steps: list[str]                  # human-readable derivation
    eligible_charges: dict[ChargeType, Decimal]   # charges that fed the designated per-unit duty
    excluded_charges: dict[ChargeType, str]       # charge -> reason it was excluded (232/IEEPA/...)
    import_date: date
    export_date: date
    claim_date: date
    within_window: bool
    flags: list[str] = field(default_factory=list)


@dataclass
class MatchedPair:
    """An assignment of export quantity to a designated import, with its recovery and trace."""

    import_entry: str
    import_line_no: int
    export_reference: str
    hts8: str
    quantity: int
    provision: DrawbackProvision
    per_unit_designated_duty: Decimal
    per_unit_comparator_duty: Optional[Decimal]   # None for direct-identification
    per_unit_recovery: Decimal
    recovery: Decimal                              # point estimate: per_unit_recovery * qty, cents
    recovery_low: Decimal                          # conservative low end (no speculative 301) (A-22)
    confidence: Confidence
    in_headline: bool                              # included in the defensible headline number?
    trace: Trace
    import_year: int = 0                           # for the by-year breakdown (import date year)


@dataclass
class BlockedItem:
    """Potential recovery the engine deliberately did NOT put in the headline, and why."""

    reason: BlockedReason
    hts8: str
    amount: Decimal               # best-estimate amount blocked (potential)
    quantity: int
    detail: str
    related_reference: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Data-quality reporting (FR1.2)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class DataQualityIssue:
    severity: str        # "error" (row dropped) | "warning" (kept, flagged)
    row: int
    field: str
    message: str


@dataclass
class DataQualityReport:
    imports_parsed: int = 0
    exports_parsed: int = 0
    imports_dropped: int = 0
    exports_dropped: int = 0
    issues: list[DataQualityIssue] = field(default_factory=list)

    def add(self, severity: str, row: int, field_: str, message: str) -> None:
        self.issues.append(DataQualityIssue(severity, row, field_, message))


# ─────────────────────────────────────────────────────────────────────────────
# Output — the Estimate (Layer 1) and the breakdowns (FR1.4-1.6)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Breakdown:
    """A reconciling slice of the headline (by year / by HTS / by program)."""

    key: str
    label: str
    recovery: Decimal
    quantity: int
    pair_count: int


@dataclass
class Estimate:
    """The instant-eligibility result. ``headline_point`` is the defensible number; ``headline_low``
    is its conservative low end; ``potential_total`` is review-needed recovery never folded into the
    headline (D-008). Everything reconciles: headline_point == Σ by_program == Σ matched-pair recovery
    where in_headline."""

    as_of: date
    tariff_config_version: str

    headline_point: Decimal
    headline_low: Decimal
    potential_total: Decimal

    eligible_duty_pool: Decimal       # total eligible duty seen (the ceiling recovery can't exceed)

    by_year: list[Breakdown]
    by_hts: list[Breakdown]
    by_program: list[Breakdown]

    blocked: list[BlockedItem]
    blocked_by_reason: dict[str, Decimal]

    matched_pairs: list[MatchedPair]
    data_quality: DataQualityReport

    filing_checklist: list[str]       # FR1.6 "what we'd need to file"
    notes: list[str] = field(default_factory=list)

    def headline_pairs(self) -> list[MatchedPair]:
        return [p for p in self.matched_pairs if p.in_headline]
