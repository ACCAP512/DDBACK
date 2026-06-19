import { useId, useState } from "react";
import type { Breakdown } from "../types";
import { int, money2, moneyCompact } from "../format";

interface Props {
  data: Breakdown[];
  /** Optional: dim bars whose key isn't in this active set (for hover sync). */
  height?: number;
  emptyText?: string;
}

interface Tip {
  x: number;
  y: number;
  title: string;
  sub: string;
}

/**
 * Hand-drawn vertical bar chart (no chart library). Linear y-scale with a few
 * gridlines, monospace value labels, and a fixed-position hover tooltip. Bars
 * use a shared green gradient defined in <defs>.
 */
export default function BarChart({ data, height = 200, emptyText }: Props) {
  const gradId = useId().replace(/:/g, "");
  const [tip, setTip] = useState<Tip | null>(null);

  if (!data.length) {
    return <div className="empty">{emptyText ?? "No data"}</div>;
  }

  const W = 680;
  const H = height;
  const padL = 8;
  const padR = 8;
  const padT = 22;
  const padB = 34;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const max = Math.max(...data.map((d) => d.recovery), 1);
  // "nice" rounded ceiling for the axis
  const niceMax = niceCeil(max);

  const n = data.length;
  const slot = plotW / n;
  const barW = Math.min(54, slot * 0.62);

  const gridLines = 4;
  const ticks = Array.from({ length: gridLines + 1 }, (_, i) => (niceMax / gridLines) * i);

  const xFor = (i: number) => padL + slot * i + (slot - barW) / 2;
  const yFor = (v: number) => padT + plotH - (v / niceMax) * plotH;

  return (
    <div style={{ position: "relative" }}>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        preserveAspectRatio="xMidYMid meet"
        onMouseLeave={() => setTip(null)}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-bright)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--accent-dim)" stopOpacity="0.55" />
          </linearGradient>
        </defs>

        {/* gridlines + y tick labels */}
        {ticks.map((t, i) => {
          const y = yFor(t);
          return (
            <g key={i}>
              <line className={i === 0 ? "axis" : "gl"} x1={padL} y1={y} x2={W - padR} y2={y} />
              <text className="gtxt" x={W - padR} y={y - 3} textAnchor="end">
                {moneyCompact(t)}
              </text>
            </g>
          );
        })}

        {/* bars */}
        {data.map((d, i) => {
          const x = xFor(i);
          const y = yFor(d.recovery);
          const h = Math.max(2, padT + plotH - y);
          return (
            <g key={d.key}>
              <rect
                className="bar"
                fill={`url(#${gradId})`}
                x={x}
                y={y}
                width={barW}
                height={h}
                rx={4}
                onMouseMove={(e) =>
                  setTip({
                    x: e.clientX,
                    y: e.clientY,
                    title: money2(d.recovery),
                    sub: `${d.label} · ${int(d.quantity)} units · ${d.pair_count} pairs`,
                  })
                }
                onMouseLeave={() => setTip(null)}
              />
              <rect className="bar-cap" x={x} y={y} width={barW} height={2} rx={1} />
              <text className="vlab" x={x + barW / 2} y={y - 6} textAnchor="middle">
                {moneyCompact(d.recovery)}
              </text>
              <text className="xlab" x={x + barW / 2} y={H - 12} textAnchor="middle">
                {shortLabel(d.key, d.label)}
              </text>
            </g>
          );
        })}
      </svg>

      {tip && (
        <div className="svgtip" style={{ left: tip.x, top: tip.y }}>
          <div className="tt">{tip.title}</div>
          <div className="ts">{tip.sub}</div>
        </div>
      )}
    </div>
  );
}

function shortLabel(key: string, label: string): string {
  // Years and HTS codes read best as the key; long program labels get trimmed.
  if (/^\d{4}$/.test(key)) return key;
  if (/^\d{6,}$/.test(key)) return key;
  return label.length > 14 ? label.slice(0, 13) + "…" : label;
}

function niceCeil(v: number): number {
  if (v <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / pow;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * pow;
}
