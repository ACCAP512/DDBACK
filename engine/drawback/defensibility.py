"""Correctness hardening — the structural substitute for human/legal review (COMPLIANCE.md §4 P6).

An INDEPENDENT post-hoc validator that consumes the engine's PUBLIC output (an ``Estimate`` and its
per-pair traces) plus the assumption registry. It does NOT touch the matcher, rules, computation, or
their tests — it only re-checks and re-partitions their output. It produces:

  (B6) DEFENSIBLE HEADLINE — depends ONLY on [VERIFIED] legal rules, as a STRUCTURAL guarantee. A pair
       contributes its conservative ``recovery_low`` to the defensible headline only if every legal,
       non-upside-only assumption in its trace is [VERIFIED]. Any claim touching an [INFERRED]/[GUESS]
       legal rule cannot add a single dollar to the defensible headline — it routes to needs-review.
       (Engineering invariants like A-16/A-23 do not gate; the speculative-301 upside A-21/A-22 is
       'upside_only' and routes its delta to review without disqualifying the floor.)

  (B7) RECONCILIATION INVARIANT — re-derives the 99% cap and the lesser-of cap per pair and the
       aggregate "total claimed refund ≤ total duty paid on claimed entries", and RAISES
       (``ReconciliationError``) on any violation. It never silently clamps.

  (B8) CITATIONS — every rule that fired carries its statutory/regulatory citation (from the registry).

  (B9) DEFENSIBILITY REPORT — a per-claim artifact (rules fired, each rule's verification tier + citation,
       the reconciliation result, the defensible-vs-review split) so a customs professional can validate
       the answer from the trace ALONE, without reading code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from drawback.assumptions import REGISTRY, Tag, get as get_assumption
from drawback.models import ZERO, Estimate, MatchedPair
from drawback.rules.computation import DRAWBACK_RATE, quantize_money

CENT = Decimal("0.01")  # one-cent tolerance for the re-derived quantized caps


class ReconciliationError(AssertionError):
    """Raised when a claimed refund exceeds the 99% cap, the lesser-of cap, or the aggregate
    claimed-≤-duty-paid invariant. We RAISE rather than silently clamp (B7) — a violation means the
    engine produced an indefensible number and must be fixed, not masked."""


@dataclass
class PairDefensibility:
    import_entry: str
    import_line_no: int
    export_reference: str
    provision: str
    in_headline: bool
    claimed: Decimal               # the engine's point recovery for this pair
    defensible: Decimal            # VERIFIED-only basis (recovery_low if basis all VERIFIED, else 0)
    review: Decimal                # claimed − defensible (needs human/licensed review)
    basis_rules: list[str]         # legal, non-upside-only assumption ids supporting the defensible amount
    basis_all_verified: bool
    blocking_rules: list[str]      # basis rules that are NOT [VERIFIED] (why defensible is 0), if any


@dataclass
class DefensibilityResult:
    defensible_headline: Decimal   # structurally [VERIFIED]-only
    best_estimate: Decimal         # = estimate.headline_point (the optimistic point)
    needs_review_total: Decimal    # everything claimed that is NOT in the defensible headline
    reconciliation_ok: bool
    total_claimed: Decimal
    duty_paid_on_claimed: Decimal
    violations: list[str]
    pairs: list[PairDefensibility] = field(default_factory=list)
    as_of: str = ""

    def report(self) -> dict:
        """B9 — the per-claim defensibility report, validatable from the trace alone."""
        rule_role: dict[str, str] = {}  # id -> "defensible" | "review"
        for pd in self.pairs:
            if pd.defensible > 0:
                for rid in pd.basis_rules:
                    rule_role[rid] = "defensible"
        rules_fired = []
        for rid in sorted(_rules_seen(self.pairs)):
            a = REGISTRY.get(rid)
            if not a:
                continue
            rules_fired.append({
                "id": a.id, "title": a.title, "tier": a.tag.value, "legal": a.legal,
                "upside_only": a.upside_only, "citations": list(a.citations),
                "contributes_to": rule_role.get(rid, "review"),
            })
        tier_summary = {t.value: sum(1 for r in rules_fired if r["tier"] == t.value) for t in Tag}
        return {
            "as_of": self.as_of,
            "defensible_headline": _f(self.defensible_headline),
            "best_estimate": _f(self.best_estimate),
            "needs_review_total": _f(self.needs_review_total),
            "headline_basis": "Only [VERIFIED] legal rules contribute to the defensible headline; any claim "
                              "touching an [INFERRED]/[GUESS] legal rule is routed to needs-review (B6).",
            "reconciliation": {
                "ok": self.reconciliation_ok,
                "invariant": "total claimed refund ≤ total duty paid on claimed entries",
                "total_claimed": _f(self.total_claimed),
                "duty_paid_on_claimed": _f(self.duty_paid_on_claimed),
                "per_pair_caps_checked": ["99% rate cap (19 CFR 190.51(b))",
                                          "lesser-of cap (19 CFR 190.32(b)(1)/190.22(a)(1)(ii))"],
                "violations": self.violations,
            },
            "tier_summary": tier_summary,
            "rules_fired": rules_fired,
            "claim_lines": [
                {
                    "import_entry": pd.import_entry, "import_line_no": pd.import_line_no,
                    "export_reference": pd.export_reference, "provision": pd.provision,
                    "in_headline": pd.in_headline, "claimed": _f(pd.claimed),
                    "defensible": _f(pd.defensible), "needs_review": _f(pd.review),
                    "basis_rules": pd.basis_rules, "basis_all_verified": pd.basis_all_verified,
                    "blocking_rules": pd.blocking_rules,
                }
                for pd in self.pairs
            ],
            "disclaimer": "Estimated potential recovery prepared by decision-support software. Not a "
                          "determination of eligibility and not legal/customs advice; a licensed customs "
                          "broker or attorney must review and file. (COMPLIANCE.md)",
        }


def _f(d: Decimal) -> float:
    return float(round(d, 2))


def _rules_seen(pairs: list[PairDefensibility]) -> set[str]:
    seen: set[str] = set()
    for pd in pairs:
        seen.update(pd.basis_rules)
    return seen


def _defensible_basis_rules(pair: MatchedPair) -> list:
    """The legal, non-upside-only assumptions supporting this pair's CONSERVATIVE (recovery_low) basis.
    Engineering invariants (legal=False) and upside-only rules (A-21/A-22) are excluded."""
    out = []
    for raw in pair.trace.assumption_ids:
        a = get_assumption(raw)
        if a and a.legal and not a.upside_only:
            out.append(a)
    return out


def harden(estimate: Estimate, *, strict: bool = True) -> DefensibilityResult:
    """Validate and re-partition the estimate. With ``strict`` (default), raises ReconciliationError on
    any cap/invariant violation. Returns the defensible/needs-review partition + the report basis."""
    defensible = ZERO
    total_claimed = ZERO
    duty_paid = ZERO
    violations: list[str] = []
    pairs: list[PairDefensibility] = []

    for p in estimate.matched_pairs:
        total_claimed += p.recovery
        duty_paid += p.per_unit_designated_duty * Decimal(p.quantity)

        # (B7) per-pair reconciliation — re-derive the caps from public fields; never clamp.
        cap99 = quantize_money(DRAWBACK_RATE * p.per_unit_designated_duty * Decimal(p.quantity))
        tag = f"{p.import_entry}/{p.import_line_no}→{p.export_reference}"
        if p.recovery > cap99 + CENT:
            violations.append(f"{tag}: recovery {p.recovery} exceeds 99% cap {cap99}")
        if p.per_unit_comparator_duty is not None:
            lcap = quantize_money(
                DRAWBACK_RATE * min(p.per_unit_designated_duty, p.per_unit_comparator_duty) * Decimal(p.quantity))
            if p.recovery > lcap + CENT:
                violations.append(f"{tag}: recovery {p.recovery} exceeds lesser-of cap {lcap}")

        # (B6) defensible amount — conservative basis, VERIFIED-only legal rules.
        basis = _defensible_basis_rules(p)
        all_verified = all(a.tag is Tag.VERIFIED for a in basis)
        blocking = [a.id for a in basis if a.tag is not Tag.VERIFIED]
        d_amt = p.recovery_low if (p.in_headline and all_verified) else ZERO
        defensible += d_amt

        pairs.append(PairDefensibility(
            import_entry=p.import_entry, import_line_no=p.import_line_no,
            export_reference=p.export_reference, provision=p.provision.value, in_headline=p.in_headline,
            claimed=p.recovery, defensible=d_amt, review=p.recovery - d_amt,
            basis_rules=[a.id for a in basis], basis_all_verified=all_verified, blocking_rules=blocking,
        ))

    # (B7) aggregate invariant: total claimed refund ≤ total duty paid on claimed entries.
    if total_claimed > duty_paid + CENT:
        violations.append(
            f"aggregate: total claimed {total_claimed} exceeds total duty paid on claimed entries {duty_paid}")

    if strict and violations:
        raise ReconciliationError("; ".join(violations))

    return DefensibilityResult(
        defensible_headline=defensible, best_estimate=estimate.headline_point,
        needs_review_total=total_claimed - defensible, reconciliation_ok=not violations,
        total_claimed=total_claimed, duty_paid_on_claimed=duty_paid, violations=violations,
        pairs=pairs, as_of=estimate.as_of.isoformat(),
    )
