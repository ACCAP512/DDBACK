// Section-301 / A-21 substitution-comparator resolution — the ONE assumption a
// claimant can resolve from their own facts (the origin / 301-eligibility of
// their substituted exports). The engine already computed, per pair, BOTH the
// point estimate (`recovery`, assumes substituted exports WOULD bear Section
// 301) and the conservative floor (`recovery_low`, assumes they would NOT).
//
// Everything here is EXACT client-side aggregation of those already-computed
// values — never new estimation. The displayed headline must never exceed the
// engine's `headline_point`.
//
//   range       (default) — show the conservative→best-estimate range as today.
//   confirmed   — claimant confirms 301-eligibility; the floor RISES to the
//                 point, the range collapses, the headline becomes FIRM.
//   overridden  — claimant says NOT 301-eligible; the headline DROPS to the
//                 conservative floor (recovery_low basis).

import type { Breakdown, Estimate, MatchedPair } from "./types";
import { useStored } from "./storage";

export type A21State = "range" | "confirmed" | "overridden";

/** The id of the registry entry this global control resolves. */
export const A21_ID = "A-21";

/** Persisted global A-21 state (localStorage("drawback-a21")). */
export function useA21(): [A21State, (s: A21State) => void] {
  const [state, setState] = useStored<A21State>("drawback-a21", "range");
  // guard against a stale/garbage persisted value
  const safe: A21State =
    state === "confirmed" || state === "overridden" ? state : "range";
  return [safe, setState];
}

/**
 * The recovery figure to use for a pair under the current A-21 resolution.
 * Only `overridden` changes anything, and only for substitution pairs whose
 * floor differs from their point (direct-ID pairs have low === point, so they
 * are unaffected in every state).
 */
export function effectiveRecovery(p: MatchedPair, state: A21State): number {
  return state === "overridden" ? p.recovery_low : p.recovery;
}

/** Does this pair carry speculative Section-301 (a non-trivial point↔floor gap)? */
export function isSubstitution301Pair(p: MatchedPair): boolean {
  return p.recovery_low < p.recovery - 0.005;
}

/** Headline pairs only (what the engine's headline_point sums over). */
export function headlinePairs(est: Estimate): MatchedPair[] {
  return est.matched_pairs.filter((p) => p.in_headline);
}

/**
 * The effective headline total.
 *   range / confirmed → Σ recovery over headline pairs (= engine headline_point)
 *   overridden        → Σ recovery_low over headline pairs (the conservative floor)
 * Never exceeds headline_point.
 */
export function effectiveHeadline(est: Estimate, state: A21State): number {
  if (state !== "overridden") return est.headline_point;
  return headlinePairs(est).reduce((a, p) => a + p.recovery_low, 0);
}

/**
 * The effective conservative floor shown on the range bar.
 *   range      → engine headline_low (unchanged)
 *   confirmed  → equals the point (range collapses; floor rises to point)
 *   overridden → equals the (now headline) floor
 */
export function effectiveLow(est: Estimate, state: A21State): number {
  if (state === "confirmed") return est.headline_point;
  if (state === "overridden") return effectiveHeadline(est, "overridden");
  return est.headline_low;
}

/**
 * Σ of the speculative-301 portion across headline substitution pairs — the
 * amount that is firmed (confirmed) or dropped (overridden). Always ≥ 0 and
 * equals headline_point − Σ recovery_low over headline pairs.
 */
export function speculative301(est: Estimate): number {
  return headlinePairs(est).reduce(
    (a, p) => a + Math.max(0, p.recovery - p.recovery_low),
    0,
  );
}

// ── exact regrouping for the `overridden` basis ─────────────────────────────
// For range/confirmed the server's point breakdowns are exactly right (they
// already equal Σ recovery). For overridden we regroup the HEADLINE pairs by
// the same key, summing recovery_low, so every breakdown keeps reconciling
// against the (lowered) headline.

type GroupKind = "year" | "hts" | "program";

function regroup(est: Estimate, kind: GroupKind): Breakdown[] {
  const map = new Map<string, Breakdown>();
  for (const p of headlinePairs(est)) {
    let key: string;
    let label: string;
    if (kind === "year") {
      key = String(p.import_year);
      label = key;
    } else if (kind === "hts") {
      key = p.hts8;
      label = p.hts8;
    } else {
      key = p.provision;
      label = p.provision;
    }
    const prev = map.get(key);
    if (prev) {
      prev.recovery += p.recovery_low;
      prev.quantity += p.quantity;
      prev.pair_count += 1;
    } else {
      map.set(key, {
        key,
        label,
        recovery: p.recovery_low,
        quantity: p.quantity,
        pair_count: 1,
      });
    }
  }
  // preserve the server's ordering/labels where we can by re-sorting like the
  // source breakdowns (recovery desc), and back-fill nicer labels from them.
  const source =
    kind === "year" ? est.by_year : kind === "hts" ? est.by_hts : est.by_program;
  const labelByKey = new Map(source.map((b) => [b.key, b.label]));
  const out = [...map.values()].map((b) => ({
    ...b,
    label: labelByKey.get(b.key) ?? b.label,
  }));
  out.sort((a, b) => b.recovery - a.recovery);
  return out;
}

/**
 * The by-year / by-HTS / by-program breakdowns under the current A-21 state.
 * range / confirmed return the server breakdowns unchanged (= point basis);
 * overridden returns exact recovery_low regroupings of the headline pairs.
 */
export function effectiveBreakdowns(
  est: Estimate,
  state: A21State,
): { byYear: Breakdown[]; byHts: Breakdown[]; byProgram: Breakdown[] } {
  if (state !== "overridden") {
    return { byYear: est.by_year, byHts: est.by_hts, byProgram: est.by_program };
  }
  return {
    byYear: regroup(est, "year"),
    byHts: regroup(est, "hts"),
    byProgram: regroup(est, "program"),
  };
}
