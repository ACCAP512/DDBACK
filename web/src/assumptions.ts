// Registry helpers: match a trace `assumption_id` (strings like
// "A-21 (comparator rate profile)") to a registry entry from GET /api/assumptions
// by its `A-\d\d` prefix, and map a tag to its badge presentation.

import type { Assumption, AssumptionsResponse, AssumptionTag } from "./types";

/** A lookup over the assumptions registry, keyed by the canonical `A-NN` id. */
export type AssumptionRegistry = Map<string, Assumption>;

/** Build a registry map from the API response (id → entry). */
export function buildRegistry(res: AssumptionsResponse | null): AssumptionRegistry {
  const m: AssumptionRegistry = new Map();
  if (!res) return m;
  for (const a of res.assumptions) {
    const id = extractAssumptionId(a.id);
    if (id) m.set(id, a);
  }
  return m;
}

/** Pull the canonical `A-NN` id out of any id/label string, e.g.
 *  "A-21 (comparator rate profile)" → "A-21". Returns null when absent. */
export function extractAssumptionId(raw: string): string | null {
  const m = raw.match(/A-\d{1,3}/i);
  return m ? m[0].toUpperCase() : null;
}

/** Look up a registry entry for a trace assumption_id (forgiving of suffixes). */
export function lookupAssumption(
  registry: AssumptionRegistry,
  raw: string,
): Assumption | undefined {
  const id = extractAssumptionId(raw);
  return id ? registry.get(id) : undefined;
}

// ── tag → badge presentation ────────────────────────────────────────────────
// Never colour-only: each carries a short label + a glyph (research §2.2 / 1.4.1).
// `cls` maps to a `.tagbadge.<cls>` style block in styles.css.

export interface TagMeta {
  label: string;
  glyph: string;
  cls: "verified" | "inferred" | "guess";
  title: string;
}

const TAG_META: Record<AssumptionTag, TagMeta> = {
  VERIFIED: {
    label: "Verified",
    glyph: "✓", // check
    cls: "verified",
    title: "Verified — a firm rule, not a judgment call.",
  },
  INFERRED: {
    label: "Inferred",
    glyph: "◉", // fisheye
    cls: "inferred",
    title: "Inferred — a defensible default the engine assumed.",
  },
  GUESS: {
    label: "Guess",
    glyph: "○", // open circle
    cls: "guess",
    title: "Guess — low-confidence; confirm from your own facts.",
  },
};

export function tagMeta(tag: AssumptionTag): TagMeta {
  return TAG_META[tag];
}
