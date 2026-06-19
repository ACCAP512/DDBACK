import type { ConfigSummary } from "../types";
import { prettyDate } from "../format";

interface Props {
  config: ConfigSummary;
}

// Curated eligible/ineligible chips. We show the headline tariff layers the
// product reasons about, in a deliberate order, rather than echoing every raw
// config key — and we route IEEPA to its CAPE track label.
const ELIGIBLE: Array<{ key: string; label: string }> = [
  { key: "base_duty", label: "Base duty" },
  { key: "section_301", label: "Section 301" },
  { key: "mpf", label: "MPF" },
  { key: "hmf", label: "HMF" },
];

const INELIGIBLE: Array<{ key: string; label: string; cape?: boolean }> = [
  { key: "section_232", label: "Section 232" },
  { key: "ieepa", label: "IEEPA → CAPE", cape: true },
  { key: "section_122", label: "Section 122" },
  { key: "ad_cvd", label: "AD/CVD" },
];

/**
 * Persistent dated banner: "Tariff eligibility as of <date>" plus eligible vs
 * excluded charge chips, sourced from /config (we filter the curated lists to
 * what the live config actually reports, so the banner can't drift from truth).
 */
export default function Banner({ config }: Props) {
  const eligibleSet = new Set(config.eligible);
  const ineligibleSet = new Set(config.ineligible);

  const elig = ELIGIBLE.filter((c) => eligibleSet.has(c.key));
  const inel = INELIGIBLE.filter((c) => ineligibleSet.has(c.key));

  return (
    <div className="banner" role="status">
      <span className="asof">
        <span className="dot" />
        Tariff eligibility as of {prettyDate(config.as_of)}
        <span className="mono faint" style={{ fontSize: 11 }}>
          ({config.version})
        </span>
      </span>

      <span className="div" aria-hidden />

      <span className="chips">
        <span className="lab">Eligible</span>
        {elig.map((c) => (
          <span className="chip ok" key={c.key} title={`${c.label} — drawback-eligible`}>
            <span className="mk" />
            {c.label}
          </span>
        ))}
      </span>

      <span className="div" aria-hidden />

      <span className="chips">
        <span className="lab">Excluded</span>
        {inel.map((c) => (
          <span
            className={`chip ${c.cape ? "cape" : "no"}`}
            key={c.key}
            title={
              c.cape
                ? "IEEPA struck down — refunded via the separate CBP CAPE process, not drawback"
                : `${c.label} — not drawback-eligible`
            }
          >
            <span className="mk" />
            {c.label}
          </span>
        ))}
      </span>
    </div>
  );
}
