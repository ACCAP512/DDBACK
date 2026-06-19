// Formatting + small domain-label helpers shared across components.

import type { ProvisionCode } from "./types";

const usd0 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const usd2 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const num = new Intl.NumberFormat("en-US");

/** Whole-dollar currency, e.g. $3,787,134. */
export const money0 = (n: number): string => usd0.format(n ?? 0);

/** Alias for whole-dollar grouped currency (used by model read-outs where
 *  trailing cents would be false precision on a simulated/aggregated value). */
export const money = money0;

/** Cents-precision currency, e.g. $20,934.12. */
export const money2 = (n: number): string => usd2.format(n ?? 0);

/** Grouped integer, e.g. 17,970. */
export const int = (n: number): string => num.format(n ?? 0);

/** Compact currency for tight chart labels, e.g. $1.0M / $260K. */
export function moneyCompact(n: number): string {
  const v = n ?? 0;
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `$${(v / 1_000).toFixed(abs >= 100_000 ? 0 : 0)}K`;
  return usd0.format(v);
}

/**
 * Two-tier formatting (research §2.2/§4): the hero, summary tiles and chart
 * labels use this abbreviated form (`$3.79M`, `$1.68M`, `$260K`); the ledger and
 * trace use full-precision `money2`. Carries 2 significant decimals at M-scale
 * so a range like `$1.68M–$3.79M` stays honest without false cent-precision.
 */
export function moneyAbbrev(n: number): string {
  const v = n ?? 0;
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 100_000) return `${sign}$${Math.round(abs / 1_000)}K`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return usd0.format(v);
}

/** Abbreviated low→high range, e.g. "$1.68M–$3.79M". */
export function moneyRange(low: number, high: number): string {
  return `${moneyAbbrev(low)}–${moneyAbbrev(high)}`;
}

/**
 * Coarse, value-suppressed figure for shaky (low-confidence / not-in-headline)
 * rows (research §2.2 VSUP): one significant figure prefixed "~" so the UI
 * resists over-reading it, e.g. "~$12K", "~$1.7M".
 */
export function moneyCoarse(n: number): string {
  const v = n ?? 0;
  const abs = Math.abs(v);
  if (abs < 1) return "$0";
  const sign = v < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}~$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) {
    // round to 1 significant figure within the K range
    const k = abs / 1_000;
    const mag = Math.pow(10, Math.floor(Math.log10(k)));
    const rounded = Math.round(k / mag) * mag;
    return `${sign}~$${rounded}K`;
  }
  const mag = Math.pow(10, Math.floor(Math.log10(abs)));
  return `${sign}~$${Math.round(abs / mag) * mag}`;
}

/** Friendly long label for a 1313 provision code. */
export function provisionLabel(code: ProvisionCode): string {
  switch (code) {
    case "58":
      return "Unused — direct identification, 19 U.S.C. 1313(j)(1)";
    case "59":
      return "Unused — substitution, 19 U.S.C. 1313(j)(2)";
    case "51":
      return "Manufacturing — direct identification, 19 U.S.C. 1313(a)";
    case "52":
      return "Manufacturing — substitution, 19 U.S.C. 1313(b)";
    case "53":
      return "Rejected merchandise, 19 U.S.C. 1313(c)";
    default:
      return `Provision ${code}`;
  }
}

/** Short provision tag for table cells. */
export function provisionShort(code: ProvisionCode): string {
  switch (code) {
    case "58":
      return "j(1) direct-ID";
    case "59":
      return "j(2) substitution";
    case "51":
      return "1313(a)";
    case "52":
      return "1313(b)";
    case "53":
      return "1313(c)";
    default:
      return code;
  }
}

/** Human label for a charge key (e.g. section_301 -> Section 301). */
export function chargeLabel(key: string): string {
  const map: Record<string, string> = {
    base_duty: "Base duty",
    section_301: "Section 301",
    section_232: "Section 232",
    section_122: "Section 122",
    ieepa: "IEEPA",
    mpf: "MPF",
    hmf: "HMF",
    ad_cvd: "AD/CVD",
    excise: "Excise",
  };
  return map[key] ?? key.replace(/_/g, " ");
}

/** Title-case-ish label for a blocked-reason key. */
export function reasonLabel(key: string): string {
  const map: Record<string, string> = {
    out_of_window: "Outside 5-year window",
    no_hts_match: "No HTS match",
    other_basket_no_match: "Other-basket, no 10-digit match",
    unused_import_duty: "Duty-paid imports, no matching export",
    ineligible_duty_only: "Only ineligible duty present",
    missing_export_proof: "Missing export proof",
    not_liquidated: "Entry not yet liquidated",
    data_quality: "Data-quality issue",
  };
  return map[key] ?? key.replace(/_/g, " ");
}

/** Format an ISO date as e.g. "May 14, 2025". */
export function prettyDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Days between two ISO dates (b - a). */
export function daysBetween(aIso: string, bIso: string): number | null {
  const a = new Date(aIso);
  const b = new Date(bIso);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return null;
  return Math.round((b.getTime() - a.getTime()) / 86_400_000);
}
