"""Top-level orchestration: a Dataset -> an explainable Estimate (Layer 1, FR1.3-1.6).

Assembles the headline point/low range, the by-year / by-HTS / by-program breakdowns, the blocked-
recovery diagnosis, and the "what we'd need to file" checklist — all reconciling to the matched pairs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from drawback.config import tariff_eligibility as cfg
from drawback.models import (
    ZERO, Breakdown, BlockedReason, Dataset, DrawbackProvision, Estimate,
)
from drawback.data.hts_reference import DEFAULT_REFERENCE
from drawback.matching.engine import match

_PROGRAM_LABEL = {
    DrawbackProvision.J2_UNUSED_SUBSTITUTION: "Unused merchandise — substitution (19 USC 1313(j)(2))",
    DrawbackProvision.J1_UNUSED_DIRECT: "Unused merchandise — direct identification (1313(j)(1))",
    DrawbackProvision.B_MFG_SUBSTITUTION: "Manufacturing — substitution (1313(b))",
    DrawbackProvision.A_MFG_DIRECT: "Manufacturing — direct identification (1313(a))",
    DrawbackProvision.C_REJECTED: "Rejected merchandise (1313(c))",
}

_REASON_LABEL = {
    BlockedReason.MISSING_EXPORT_PROOF: "Missing export proof (recoverable once a B/L or AES ITN is supplied)",
    BlockedReason.OUT_OF_WINDOW: "Outside the 5-year window (unrecoverable)",
    BlockedReason.INELIGIBLE_DUTY_ONLY: "Ineligible duty layer (not drawback-eligible)",
    BlockedReason.NO_HTS_MATCH: "No duty-paid import under the same 8-digit subheading",
    BlockedReason.NOT_LIQUIDATED: "Import entry not finally liquidated",
    BlockedReason.UNUSED_IMPORT_DUTY: "Duty-paid imports with no matching export to designate",
    BlockedReason.OTHER_BASKET_NO_MATCH: "'Other'-basket HTS — no permissible substitution",
    BlockedReason.DATA_QUALITY: "Data-quality issue",
}


def _sum(values) -> Decimal:
    return sum(values, ZERO)


def build_estimate(
    dataset: Dataset,
    claim_date: Optional[date] = None,
    ref=DEFAULT_REFERENCE,
) -> Estimate:
    claim_date = claim_date or cfg.AS_OF
    res = match(dataset.imports, dataset.exports, claim_date, ref)

    headline_pairs = [p for p in res.pairs if p.in_headline]
    potential_pairs = [p for p in res.pairs if not p.in_headline]

    headline_point = _sum(p.recovery for p in headline_pairs)
    headline_low = _sum(p.recovery_low for p in headline_pairs)
    potential_total = _sum(p.recovery for p in potential_pairs)

    # ── breakdowns over the HEADLINE pairs (they reconcile to headline_point) ──
    by_year = _group(headline_pairs, key=lambda p: str(p.import_year), label=lambda p: str(p.import_year))
    by_hts = _group(headline_pairs, key=lambda p: p.hts8,
                    label=lambda p: f"{p.hts8} — {ref.description(p.hts8)}")
    by_program = _group(headline_pairs, key=lambda p: p.provision.value,
                        label=lambda p: _PROGRAM_LABEL.get(p.provision, p.provision.value))

    # ── blocked-by-reason aggregation: unmatched (res.blocked) + matched-but-needs-review (potential) ──
    blocked_by_reason: dict[str, Decimal] = {}
    for b in res.blocked:
        blocked_by_reason[b.reason.value] = blocked_by_reason.get(b.reason.value, ZERO) + b.amount
    for p in potential_pairs:
        if any("missing_export_proof" in f for f in p.trace.flags):
            k = BlockedReason.MISSING_EXPORT_PROOF.value
        elif any("not_finally_liquidated" in f for f in p.trace.flags):
            k = BlockedReason.NOT_LIQUIDATED.value
        else:
            continue
        blocked_by_reason[k] = blocked_by_reason.get(k, ZERO) + p.recovery

    filing_checklist = _build_checklist(res, potential_pairs, headline_point)

    notes = [
        f"Tariff-eligibility config {cfg.VERSION} as of {cfg.AS_OF.isoformat()}. "
        "Eligible: base duty, Section 301, MPF, HMF, importation excise. "
        "Excluded: Section 232, IEEPA (CAPE track), Section 122, AD/CVD.",
        "Headline is the defensible, proof-backed recovery. The range low end excludes speculative "
        "Section 301 from the substitution comparator (A-22). Potential is matched-but-needs-review.",
        "Preparation/decision-support only — not the filer of record, not legal advice (19 CFR 190.6).",
    ]

    return Estimate(
        as_of=cfg.AS_OF,
        tariff_config_version=cfg.VERSION,
        headline_point=headline_point,
        headline_low=headline_low,
        potential_total=potential_total,
        eligible_duty_pool=res.eligible_duty_pool,
        by_year=by_year,
        by_hts=by_hts,
        by_program=by_program,
        blocked=res.blocked,
        blocked_by_reason=blocked_by_reason,
        matched_pairs=res.pairs,
        data_quality=dataset.data_quality,
        filing_checklist=filing_checklist,
        notes=notes,
    )


def _group(pairs, key, label) -> list[Breakdown]:
    buckets: dict[str, list] = {}
    labels: dict[str, str] = {}
    for p in pairs:
        k = key(p)
        buckets.setdefault(k, []).append(p)
        labels[k] = label(p)
    out = [
        Breakdown(key=k, label=labels[k], recovery=_sum(p.recovery for p in ps),
                  quantity=sum(p.quantity for p in ps), pair_count=len(ps))
        for k, ps in buckets.items()
    ]
    out.sort(key=lambda b: b.recovery, reverse=True)
    return out


def _build_checklist(res, potential_pairs, headline_point) -> list[str]:
    items: list[str] = []
    missing_proof = _sum(p.recovery for p in potential_pairs
                         if any("missing_export_proof" in f for f in p.trace.flags))
    not_liquidated = _sum(p.recovery for p in potential_pairs
                          if any("not_finally_liquidated" in f for f in p.trace.flags))
    out_of_window = _sum(b.amount for b in res.blocked if b.reason is BlockedReason.OUT_OF_WINDOW)

    if missing_proof > 0:
        items.append(f"Obtain export proof (bill of lading / AES ITN) for ${missing_proof:,.2f} of matched "
                     "exports to move them into the defensible headline (19 CFR 190.72).")
    if not_liquidated > 0:
        items.append(f"Confirm final liquidation of the import entries behind ${not_liquidated:,.2f} of "
                     "potential recovery (19 CFR 190.3(a)).")
    if out_of_window > 0:
        items.append(f"Note: ${out_of_window:,.2f} of potential recovery is already outside the 5-year "
                     "window and is unrecoverable (19 USC 1313(r)).")
    if res.ieepa_total > 0:
        items.append(f"IEEPA duties (${res.ieepa_total:,.2f}) are not drawback — pursue them via the separate "
                     "CBP CAPE refund process (struck down by SCOTUS 2026-02-20).")
    if headline_point > 0:
        items.extend([
            "Engage a licensed customs broker/filer (or self-file with a CBP entry filer code + certified "
            "ABI software) to certify and transmit — this tool prepares; a human/broker files (19 CFR 190.6).",
            "Consider applying for the Accelerated Payment privilege + a sufficient 1A bond to receive the "
            "refund in ~3 weeks rather than after liquidation (19 CFR 190.92).",
            "Retain all supporting records for 3 years from liquidation of the claim (19 CFR 190.15).",
        ])
    return items
