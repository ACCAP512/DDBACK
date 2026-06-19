// Best-effort legal-citation linkifier (research §2.3). Turns the engine's
// rule_citations into live deep links:
//   "19 CFR 190.32(b)(1)" → eCFR section page
//   "19 U.S.C. 1313(j)(2)" → Cornell LII US Code text
// Parsing is intentionally forgiving; anything we can't confidently parse is
// returned with href:null so the caller renders it as plain text.

export interface ParsedCite {
  /** the original citation string, verbatim */
  text: string;
  /** resolved URL, or null when unparseable */
  href: string | null;
  /** which source the link points at (for the small badge), if any */
  source?: "eCFR" | "Cornell LII";
}

// 19 CFR 190.32  /  19 C.F.R. § 190.32(b)(1)
const CFR_RE = /\b(\d+)\s*C\.?\s*F\.?\s*R\.?\s*§?\s*(\d+)\.(\d+)/i;
// 19 U.S.C. 1313  /  19 USC § 1313(j)(2)
const USC_RE = /\b(\d+)\s*U\.?\s*S\.?\s*C\.?\s*§?\s*(\d+)/i;

/** Resolve a single citation string to a link (best-effort). */
export function parseCitation(raw: string): ParsedCite {
  const text = raw.trim();

  const cfr = text.match(CFR_RE);
  if (cfr) {
    const [, title, part, section] = cfr;
    return {
      text,
      source: "eCFR",
      href: `https://www.ecfr.gov/current/title-${title}/part-${part}/section-${part}.${section}`,
    };
  }

  const usc = text.match(USC_RE);
  if (usc) {
    const [, title, section] = usc;
    return {
      text,
      source: "Cornell LII",
      href: `https://www.law.cornell.edu/uscode/text/${title}/${section}`,
    };
  }

  return { text, href: null };
}

/** Count the distinct CFR references in a list of citations (for "N CFR refs"). */
export function cfrRefCount(citations: string[]): number {
  let n = 0;
  for (const c of citations) if (CFR_RE.test(c)) n++;
  return n;
}
