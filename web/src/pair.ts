// Pair identity + a one-line plain-language basis, shared by the grid, the
// trace drawer and the standalone printable page.

import type { Estimate, MatchedPair } from "./types";
import { confidenceMeta } from "./components/ui";

/** Stable id for a matched pair: `${import_entry}.${import_line_no}~${export_reference}`. */
export function pairId(p: MatchedPair): string {
  return `${p.import_entry}.${p.import_line_no}~${p.export_reference}`;
}

/** Find a pair in an estimate by its id (for hash-routing). */
export function findPair(est: Estimate, id: string): MatchedPair | undefined {
  return est.matched_pairs.find((p) => pairId(p) === id);
}

/** Count of evidence items present + CFR refs, for the row/drawer summary. */
export function evidenceSummary(p: MatchedPair): { items: number; cfr: number } {
  const t = p.trace;
  // evidence "items" = the manifest rows that are satisfied (import entry,
  // export proof, in-window) — mirrors EvidenceManifest's have-count.
  let items = 1; // duty-paid import entry is always present
  const missingProof =
    !p.in_headline && (p.confidence === "low" || t.flags.some((f) => /proof|export/i.test(f)));
  if (!missingProof) items += 1;
  if (t.within_window) items += 1;
  return { items, cfr: t.rule_citations.length };
}

/** The confidence → bound-action line (research §2.2/§2.3 Level-1). */
export function confidenceAction(p: MatchedPair): { label: string; action: string } {
  const m = confidenceMeta(p.confidence);
  return { label: m.label, action: m.action };
}

/** One-line plain-language basis for Level 1. */
export function plainBasis(p: MatchedPair): string {
  const t = p.trace;
  const direct = t.match_basis === "direct_identification";
  const prog =
    p.provision === "58" || p.provision === "51"
      ? "direct-identification"
      : "substitution";
  const lead = direct
    ? `This export is the same merchandise as the import (direct identification), so duty is recoverable with no lesser-of cap`
    : `A ${prog} match links eligible duty-paid imports to this export under the lesser-of comparator`;
  const window = t.within_window
    ? "within the 5-year drawback window"
    : "but it falls outside the 5-year window";
  return `${lead}, ${window}.`;
}
