// FEATURE 3 — by-year recovery chart on Recharts v3 (research §3, the a11y
// "safer default"). Recharts v3's accessibilityLayer is ON, giving keyboard
// navigation + ARIA for free. Themed to the design tokens (bar = --accent;
// axis/grid muted via --ink-2 / --line) and re-rendered on theme change so it
// tracks light/dark. Custom tooltip shows the year + full-precision money2.
// Deliberately minimal chrome — not a stock dashboard.

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart as RBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Breakdown } from "../types";
import { money2, moneyAbbrev } from "../format";

interface Props {
  data: Breakdown[];
  height?: number;
  emptyText?: string;
}

interface Tokens {
  accent: string;
  accentBright: string;
  ink2: string;
  ink3: string;
  line: string;
}

/** Read the live themed colours off :root so the chart matches both themes. */
function readTokens(): Tokens {
  const cs = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) =>
    cs.getPropertyValue(name).trim() || fallback;
  return {
    accent: v("--accent", "#097552"),
    accentBright: v("--accent-bright", "#0e9268"),
    ink2: v("--ink-2", "#545f70"),
    ink3: v("--ink-3", "#6b7585"),
    line: v("--line", "rgba(17,24,39,0.1)"),
  };
}

export default function YearChart({ data, height = 210, emptyText }: Props) {
  // re-read tokens on mount and whenever <html data-theme> flips, so the chart
  // tracks the light/dark toggle without threading theme through props.
  const [tokens, setTokens] = useState<Tokens>(() => readTokens());
  useEffect(() => {
    const root = document.documentElement;
    const obs = new MutationObserver(() => setTokens(readTokens()));
    obs.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
    setTokens(readTokens());
    return () => obs.disconnect();
  }, []);

  if (!data.length) {
    return <div className="empty">{emptyText ?? "No data"}</div>;
  }

  const rows = data.map((d) => ({
    key: d.key,
    label: shortLabel(d.key, d.label),
    recovery: d.recovery,
    quantity: d.quantity,
    pair_count: d.pair_count,
  }));

  const total = rows.reduce((a, r) => a + r.recovery, 0);
  const ariaLabel =
    `Recovery by import year. ${rows.length} years, total ${moneyAbbrev(total)}. ` +
    rows.map((r) => `${r.label}: ${moneyAbbrev(r.recovery)}`).join("; ") + ".";

  return (
    <div className="rchart" style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RBarChart
          data={rows}
          margin={{ top: 18, right: 6, bottom: 4, left: 4 }}
          accessibilityLayer
          aria-label={ariaLabel}
          barCategoryGap="28%"
        >
          <CartesianGrid
            vertical={false}
            stroke={tokens.line}
            strokeDasharray="2 4"
          />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={{ stroke: tokens.line }}
            tick={{ fill: tokens.ink2, fontSize: 11, fontFamily: "var(--mono)" }}
            interval={0}
            dy={4}
          />
          <YAxis
            tickFormatter={(v: number) => moneyAbbrev(v)}
            tickLine={false}
            axisLine={false}
            width={54}
            tick={{ fill: tokens.ink3, fontSize: 10, fontFamily: "var(--mono)" }}
          />
          <Tooltip
            cursor={{ fill: tokens.accent, fillOpacity: 0.08 }}
            content={<YearTip />}
          />
          <Bar
            dataKey="recovery"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
            maxBarSize={56}
          >
            {rows.map((r) => (
              <Cell key={r.key} fill={tokens.accentBright} />
            ))}
          </Bar>
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TipPayload {
  payload: { label: string; recovery: number; quantity: number; pair_count: number };
}
function YearTip({ active, payload }: { active?: boolean; payload?: TipPayload[] }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rtip">
      <div className="tt">{money2(d.recovery)}</div>
      <div className="ts">
        {d.label} · {d.quantity.toLocaleString("en-US")} units · {d.pair_count} pairs
      </div>
    </div>
  );
}

function shortLabel(key: string, label: string): string {
  if (/^\d{4}$/.test(key)) return key;
  if (/^\d{6,}$/.test(key)) return key;
  return label.length > 14 ? label.slice(0, 13) + "…" : label;
}
