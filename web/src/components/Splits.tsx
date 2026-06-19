import type { Breakdown } from "../types";
import { int, money2, provisionShort } from "../format";

interface Props {
  data: Breakdown[];
  total: number;
  variant: "program" | "hts";
}

/**
 * Horizontal split bars for by-program / by-HTS breakdowns. Each meter is sized
 * relative to the largest slice so small slices stay visible; the share-of-
 * headline percentage is shown in the meta line.
 */
export default function Splits({ data, total, variant }: Props) {
  if (!data.length) return <div className="empty">No breakdown available</div>;

  const max = Math.max(...data.map((d) => d.recovery), 1);

  return (
    <div className="splits">
      {data.map((d) => {
        const share = total > 0 ? (d.recovery / total) * 100 : 0;
        const w = (d.recovery / max) * 100;
        return (
          <div className="split" key={d.key}>
            <div className="row1">
              <span className="nm">{renderName(d, variant)}</span>
              <span className="amt">{money2(d.recovery)}</span>
            </div>
            <div className="meter">
              <span style={{ width: `${Math.max(1.5, w)}%` }} />
            </div>
            <div className="meta">
              {share.toFixed(1)}% of headline · {int(d.quantity)} units · {d.pair_count} pairs
            </div>
          </div>
        );
      })}
    </div>
  );
}

function renderName(d: Breakdown, variant: "program" | "hts") {
  if (variant === "program") {
    return (
      <>
        <span className="code">{provisionShort(d.key)}</span>
        {stripProvisionPrefix(d.label)}
      </>
    );
  }
  // HTS: label already looks like "85044095 — Static converters …"
  const [code, ...rest] = d.label.split(" — ");
  if (rest.length) {
    return (
      <>
        <span className="code">{code}</span>
        {rest.join(" — ")}
      </>
    );
  }
  return (
    <>
      <span className="code">{d.key}</span>
      {d.label}
    </>
  );
}

function stripProvisionPrefix(label: string): string {
  // by_program labels are already full ("Unused merchandise — substitution …")
  return label;
}
