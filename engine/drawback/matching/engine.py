"""The matching engine (the moat). Assigns export quantities to designated imports to MAXIMISE total
recoverable duty subject to the verified rules, with a full trace per matched pair.

Approach (DECISIONS D-004 / ASSUMPTIONS A-10, A-23):
  * Decompose into independent buckets keyed on the 8-digit HTS substitution standard (A-01), with the
    "other"-basket exception collapsing a bucket to a 10-digit key (A-02).
  * Within each bucket run an exact integer min-cost max-flow (maximise recovery, conserve quantity so
    no duty/export is claimed twice — A-10) in TWO passes:
       Pass 1 (headline)   : liquidated imports w/ eligible duty  ×  proof-backed, in-window exports.
       Pass 2 (potential)  : residual import capacity (+ not-liquidated imports)  ×  remaining exports
                             (missing-proof / not-liquidated) — recovery surfaced as "needs review",
                             never folded into the headline.
  * Conservatism: the headline takes first claim on import duty using only fully-defensible exports; the
    range low end recomputes the same pairs without speculative Section 301 (A-21/A-22).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Optional

from drawback.models import (
    ZERO, BlockedItem, BlockedReason, ChargeType, Confidence, DrawbackProvision,
    ExportLine, ImportLine, MatchBasis, MatchedPair,
)
from drawback.rules import computation as comp
from drawback.rules import eligibility as elig_rules
from drawback.rules import time_windows
from drawback.rules.hts import hts8, normalize_hts, substitution_match
from drawback.matching.mcmf import MinCostFlow
from drawback.matching.trace import build_trace

# Decimal dollars -> integer micro-dollars for the optimizer's arc costs. The assignment DECISION is
# made on scaled ints (exact, integral); the reported money is recomputed exactly in Decimal (A-16).
SCALE = 10 ** 6


def _scaled(per_unit_recovery: Decimal) -> int:
    return -int((per_unit_recovery * SCALE).to_integral_value(rounding=ROUND_HALF_UP))


@dataclass
class _Imp:
    idx: int
    line: ImportLine
    eligible: comp.EligibleDuty
    eligible_qty: int
    headline: bool          # liquidated AND has eligible duty


@dataclass
class _Exp:
    idx: int
    line: ExportLine
    comp_point: Decimal     # comparator per unit incl. speculative 301
    comp_low: Decimal       # comparator per unit excl. speculative 301


@dataclass
class MatchResult:
    pairs: list[MatchedPair]
    blocked: list[BlockedItem]
    eligible_duty_pool: Decimal
    ineligible_total: Decimal       # 232/122/AD-CVD — not drawback-eligible
    ieepa_total: Decimal            # routed to the separate CAPE track (A-13)
    notes: list[str] = field(default_factory=list)


def _bucket_key(hts10: str, ref) -> Optional[tuple[str, str]]:
    """Substitution bucket key. None means the merchandise cannot substitute at all (8-digit AND
    10-digit descriptions both begin with 'other', A-02)."""
    h8 = hts8(hts10)
    if ref.begins_with_other(h8):
        h10 = normalize_hts(hts10)
        if ref.begins_with_other_10(h10):
            return None
        return ("10", h10)
    return ("8", h8)


def _arc_recovery(imp: _Imp, exp: _Exp, ref) -> tuple[DrawbackProvision, MatchBasis, Decimal, Decimal, Optional[Decimal], str]:
    """Per-unit recovery (point, low), provision, basis, comparator, and reason for one (import,export)."""
    same_hts10 = normalize_hts(imp.line.hts10) == normalize_hts(exp.line.hts10)
    is_direct = (
        exp.line.direct_id_entry == imp.line.entry_number
        and exp.line.direct_id_line == imp.line.line_number
        and same_hts10
    )
    if is_direct:
        base = comp.direct_identification_per_unit(imp.eligible.per_unit)
        pu = comp.apply_recovered_materials(base, exp.line.recovered_value_per_unit)
        reason = "direct identification — exported units identified from this import lot (19 CFR 190.14)"
        return DrawbackProvision.J1_UNUSED_DIRECT, MatchBasis.DIRECT_IDENTIFICATION, pu, pu, None, reason

    allowed, basis, reason = substitution_match(imp.line.hts10, exp.line.hts10, ref)
    basis = basis or MatchBasis.SUBSTITUTION_8_DIGIT
    pu_point = comp.apply_recovered_materials(
        comp.unused_substitution_per_unit(imp.eligible.per_unit, exp.comp_point), exp.line.recovered_value_per_unit)
    pu_low = comp.apply_recovered_materials(
        comp.unused_substitution_per_unit(imp.eligible.per_unit, exp.comp_low), exp.line.recovered_value_per_unit)
    return DrawbackProvision.J2_UNUSED_SUBSTITUTION, basis, pu_point, pu_low, exp.comp_point, reason


def _solve_bucket(
    imps: list[_Imp],
    exps: list[_Exp],
    imp_cap: dict[int, int],
    exp_cap: dict[int, int],
    claim_date: date,
    ref,
    arc_allowed: Callable[[_Imp, _Exp], bool],
) -> list[tuple[int, int, int]]:
    """Run one MCMF pass over a bucket. Returns matched (imp_idx, exp_idx, qty) triples.
    Arc inclusion is gated by ``arc_allowed`` and by the 5-year window."""
    active_imps = [im for im in imps if imp_cap.get(im.idx, 0) > 0]
    active_exps = [ex for ex in exps if exp_cap.get(ex.idx, 0) > 0]
    if not active_imps or not active_exps:
        return []

    n_i, n_e = len(active_imps), len(active_exps)
    SRC, SINK = 0, 1 + n_i + n_e
    g = MinCostFlow(SINK + 1)
    imp_node = {im.idx: 1 + k for k, im in enumerate(active_imps)}
    exp_node = {ex.idx: 1 + n_i + k for k, ex in enumerate(active_exps)}

    for im in active_imps:
        g.add_edge(SRC, imp_node[im.idx], imp_cap[im.idx], 0)
    for ex in active_exps:
        g.add_edge(exp_node[ex.idx], SINK, exp_cap[ex.idx], 0)

    edge_meta: dict[int, tuple[int, int]] = {}
    for im in active_imps:
        for ex in active_exps:
            if not arc_allowed(im, ex):
                continue
            ok, _reason = time_windows.export_placement_ok(im.line.import_date, ex.line.export_date, claim_date)
            if not ok:
                continue
            _prov, _basis, pu_point, _pu_low, _cmp, _r = _arc_recovery(im, ex, ref)
            if pu_point <= ZERO:
                continue
            cap = min(imp_cap[im.idx], exp_cap[ex.idx])
            eid = g.add_edge(imp_node[im.idx], exp_node[ex.idx], cap, _scaled(pu_point))
            edge_meta[eid] = (im.idx, ex.idx)

    g.solve(SRC, SINK)

    matched: list[tuple[int, int, int]] = []
    for eid, (i_idx, e_idx) in edge_meta.items():
        f = g.flow_on(eid)
        if f > 0:
            matched.append((i_idx, e_idx, f))
    return matched


def match(imports: list[ImportLine], exports: list[ExportLine], claim_date: date, ref) -> MatchResult:
    # ── precompute import / export structures ───────────────────────────────
    imps: list[_Imp] = []
    eligible_pool = ZERO
    ineligible_total = ZERO
    ieepa_total = ZERO
    for idx, line in enumerate(imports):
        ed = comp.eligible_per_unit_duty(line.charges, line.quantity)
        eligible_pool += ed.total_eligible
        for charge, amt in line.charges.items():
            if charge == ChargeType.IEEPA:
                ieepa_total += amt
            elif charge in (ChargeType.SECTION_232, ChargeType.SECTION_122, ChargeType.AD_CVD):
                ineligible_total += amt
        has_dut = ed.total_eligible > 0
        imps.append(_Imp(idx, line, ed, line.quantity if has_dut else 0,
                         headline=has_dut and line.liquidated))

    exps: list[_Exp] = []
    for idx, line in enumerate(exports):
        cp = comp.comparator_per_unit_duty(line.hts10, line.value_per_unit, ref, include_speculative_301=True)
        cl = comp.comparator_per_unit_duty(line.hts10, line.value_per_unit, ref, include_speculative_301=False)
        exps.append(_Exp(idx, line, cp.per_unit, cl.per_unit))

    # ── bucket by substitution key ──────────────────────────────────────────
    buckets: dict[tuple[str, str], tuple[list[_Imp], list[_Exp]]] = {}
    unbucketable_exports: list[_Exp] = []
    for im in imps:
        key = _bucket_key(im.line.hts10, ref)
        if key is None:
            continue
        buckets.setdefault(key, ([], []))[0].append(im)
    for ex in exps:
        key = _bucket_key(ex.line.hts10, ref)
        if key is None:
            unbucketable_exports.append(ex)
            continue
        buckets.setdefault(key, ([], []))[1].append(ex)

    imp_remaining = {im.idx: im.eligible_qty for im in imps}
    exp_remaining = {ex.idx: ex.line.quantity for ex in exps}
    pairs: list[MatchedPair] = []
    exp_matched_qty: dict[int, int] = {ex.idx: 0 for ex in exps}

    def _emit(i_idx: int, e_idx: int, qty: int, in_headline: bool) -> None:
        im = imps[i_idx]
        ex = exps[e_idx]
        prov, basis, pu_point, pu_low, cmp_pu, reason = _arc_recovery(im, ex, ref)
        within = True  # only feasible (in-window) arcs reach here
        has_proof = ex.line.has_export_proof
        confidence, headline_ok, flags = elig_rules.pair_confidence(has_proof, within, im.line.liquidated)
        in_head = in_headline and headline_ok
        rec_point = comp.line_recovery(pu_point, qty)
        rec_low = comp.line_recovery(pu_low, qty)
        trace = build_trace(
            provision=prov, basis=basis,
            designated_per_unit=im.eligible.per_unit, comparator_per_unit=cmp_pu,
            per_unit_recovery=pu_point, quantity=qty, recovery=rec_point,
            eligible_charges=im.eligible.eligible_charges, excluded_charges=im.eligible.excluded_charges,
            import_date=im.line.import_date, export_date=ex.line.export_date, claim_date=claim_date,
            within_window=within, hts_match_reason=reason, extra_flags=flags,
        )
        pairs.append(MatchedPair(
            import_entry=im.line.entry_number, import_line_no=im.line.line_number,
            export_reference=ex.line.reference, hts8=im.line.hts8, quantity=qty, provision=prov,
            per_unit_designated_duty=im.eligible.per_unit, per_unit_comparator_duty=cmp_pu,
            per_unit_recovery=pu_point, recovery=rec_point, recovery_low=rec_low,
            confidence=confidence, in_headline=in_head, trace=trace, import_year=im.line.import_date.year,
        ))
        imp_remaining[i_idx] -= qty
        exp_remaining[e_idx] -= qty
        exp_matched_qty[e_idx] += qty

    # ── Pass 1 — headline ───────────────────────────────────────────────────
    for (b_imps, b_exps) in buckets.values():
        cap_i = {im.idx: (im.eligible_qty if im.headline else 0) for im in b_imps}
        cap_e = {ex.idx: (ex.line.quantity if ex.line.has_export_proof else 0) for ex in b_exps}
        for i_idx, e_idx, qty in _solve_bucket(
            b_imps, b_exps, cap_i, cap_e, claim_date, ref,
            arc_allowed=lambda im, ex: im.headline and ex.line.has_export_proof,
        ):
            _emit(i_idx, e_idx, qty, in_headline=True)

    # ── Pass 2 — potential (needs review) ──────────────────────────────────
    for (b_imps, b_exps) in buckets.values():
        cap_i = {im.idx: imp_remaining[im.idx] for im in b_imps}
        cap_e = {ex.idx: exp_remaining[ex.idx] for ex in b_exps}
        for i_idx, e_idx, qty in _solve_bucket(
            b_imps, b_exps, cap_i, cap_e, claim_date, ref,
            arc_allowed=lambda im, ex: im.eligible_qty > 0,  # residual capacity already bounds it
        ):
            _emit(i_idx, e_idx, qty, in_headline=False)

    blocked = _diagnose_blocked(imps, exps, buckets, unbucketable_exports, imp_remaining,
                                exp_matched_qty, claim_date, ref, ineligible_total, ieepa_total)
    return MatchResult(pairs=pairs, blocked=blocked, eligible_duty_pool=eligible_pool,
                       ineligible_total=ineligible_total, ieepa_total=ieepa_total)


def _diagnose_blocked(imps, exps, buckets, unbucketable_exports, imp_remaining, exp_matched_qty,
                      claim_date, ref, ineligible_total, ieepa_total) -> list[BlockedItem]:
    """Explain the gap between the headline and the theoretical maximum (FR1.5/FR1.6). Non-overlapping
    with the matched pairs: these are amounts NOT represented by any pair."""
    blocked: list[BlockedItem] = []
    bucket_imps_by_key = {k: v[0] for k, v in buckets.items()}

    for ex in exps:
        unmatched = ex.line.quantity - exp_matched_qty.get(ex.idx, 0)
        if unmatched <= 0:
            continue
        indicative = comp.line_recovery(comp.DRAWBACK_RATE * ex.comp_point, unmatched)
        key = _bucket_key(ex.line.hts10, ref)
        if key is None:
            reason, detail = BlockedReason.OTHER_BASKET_NO_MATCH, (
                "8-digit and 10-digit descriptions both begin with 'other' — no substitution permitted (1313(j)(5))")
        else:
            b_imps = bucket_imps_by_key.get(key, [])
            eligible_imps = [im for im in b_imps if im.eligible_qty > 0]
            if not eligible_imps:
                reason, detail = BlockedReason.NO_HTS_MATCH, (
                    "no duty-paid import under the same 8-digit subheading to designate against")
            else:
                any_in_window = any(
                    time_windows.export_placement_ok(im.line.import_date, ex.line.export_date, claim_date)[0]
                    for im in eligible_imps)
                if not any_in_window:
                    reason, detail = BlockedReason.OUT_OF_WINDOW, (
                        "matching duty-paid imports exist but all fall outside the 5-year window (1313(r))")
                else:
                    # In-window eligible imports exist but their duty was exhausted -> no remaining duty.
                    reason, detail = BlockedReason.UNUSED_IMPORT_DUTY, (
                        "exported quantity exceeds available duty-paid import quantity in this subheading")
        if reason is BlockedReason.UNUSED_IMPORT_DUTY:
            continue  # this is an export surplus, not blocked recovery; skip to avoid overstating
        blocked.append(BlockedItem(reason=reason, hts8=ex.line.hts8, amount=indicative,
                                   quantity=unmatched, detail=detail, related_reference=ex.line.reference))

    # Unused import duty: eligible duty with no export to justify it (informational).
    for im in imps:
        rem = imp_remaining.get(im.idx, 0)
        if rem > 0 and im.eligible.per_unit > 0:
            amt = comp.line_recovery(comp.DRAWBACK_RATE * im.eligible.per_unit, rem)
            if amt > 0:
                blocked.append(BlockedItem(
                    reason=BlockedReason.UNUSED_IMPORT_DUTY, hts8=im.line.hts8, amount=amt, quantity=rem,
                    detail="duty-paid import units with no matching export/destruction to designate",
                    related_reference=f"{im.line.entry_number}/{im.line.line_number}"))

    # Ineligible duty layers (not recoverable via drawback) — surfaced, never counted as recovery.
    if ineligible_total > 0:
        blocked.append(BlockedItem(
            reason=BlockedReason.INELIGIBLE_DUTY_ONLY, hts8="—", amount=ineligible_total, quantity=0,
            detail="Section 232 / Section 122 / AD-CVD duties are not drawback-eligible (19 CFR 190.3(b); 1677h)"))
    if ieepa_total > 0:
        blocked.append(BlockedItem(
            reason=BlockedReason.INELIGIBLE_DUTY_ONLY, hts8="IEEPA", amount=ieepa_total, quantity=0,
            detail="IEEPA duties were struck down (SCOTUS 2026-02-20) — recoverable via the separate CAPE "
                   "process, NOT drawback (A-13)"))
    return blocked
