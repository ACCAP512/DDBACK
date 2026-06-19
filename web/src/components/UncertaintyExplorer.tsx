// FEATURE 2 — Quantile-dotplot uncertainty explorer (research §2.3, "feel a
// range without misreading it"). A clearly-SECONDARY, collapsible sensitivity
// analysis tied to the same A-21 question. NOT a measurement.
//
// Slider P = "Assume each substituted export independently has a P% chance of
// bearing Section 301 if imported." For each headline substitution pair the
// contribution is `recovery` with prob P else `recovery_low`; firm pairs are
// constant. We run a SEEDED client-side Monte Carlo (mulberry32, fixed seed) so
// the picture is deterministic, sum per trial, and draw a 20-dot quantile
// dotplot (each dot = 5% probability mass) on a $ axis spanning floor…point,
// marking the mean and shading P10–P90. The endpoints wire to Feature 1:
// P=100% = Confirm, P=0% = Override.

import { useEffect, useMemo, useState } from "react";
import type { Estimate } from "../types";
import type { A21State } from "../a21";
import { headlinePairs, isSubstitution301Pair } from "../a21";
import { mulberry32 } from "../random";
import { money, moneyAbbrev } from "../format";

interface Props {
  est: Estimate;
  a21: A21State;
  setA21: (s: A21State) => void;
}

const TRIALS = 2000;
const SEED = 0x9e3779b9; // fixed → deterministic dotplot
const DOTS = 20; // each dot = 5% probability mass

/** Honour prefers-reduced-motion (no dot transition when set). */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!mq) return;
    setReduced(mq.matches);
    const on = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

export default function UncertaintyExplorer({ est, a21, setA21 }: Props) {
  const reduced = usePrefersReducedMotion();
  const [open, setOpen] = useState(false);
  // P seeds from the current A-21 state so the two controls feel connected.
  const [p, setP] = useState<number>(() =>
    a21 === "overridden" ? 0 : 100,
  );

  // keep P in step when the global A-21 control moves to an endpoint
  useEffect(() => {
    if (a21 === "confirmed") setP(100);
    else if (a21 === "overridden") setP(0);
  }, [a21]);

  // headline substitution pairs (firm direct-ID pairs add a constant base)
  const { subPairs, base, floor, point } = useMemo(() => {
    const heads = headlinePairs(est);
    const subs = heads.filter(isSubstitution301Pair);
    const constant = heads
      .filter((h) => !isSubstitution301Pair(h))
      .reduce((a, h) => a + h.recovery, 0);
    const lo = heads.reduce((a, h) => a + h.recovery_low, 0);
    const hi = heads.reduce((a, h) => a + h.recovery, 0);
    return { subPairs: subs, base: constant, floor: lo, point: hi };
  }, [est]);

  // Monte Carlo → sorted totals (deterministic for a given P)
  const sorted = useMemo(() => {
    const prob = p / 100;
    const lows = subPairs.map((s) => s.recovery_low);
    const highs = subPairs.map((s) => s.recovery);
    const rng = mulberry32(SEED);
    const totals = new Float64Array(TRIALS);
    for (let t = 0; t < TRIALS; t++) {
      let sum = base;
      for (let i = 0; i < subPairs.length; i++) {
        sum += rng() < prob ? highs[i] : lows[i];
      }
      totals[t] = sum;
    }
    const arr = Array.from(totals);
    arr.sort((a, b) => a - b);
    return arr;
  }, [subPairs, base, p]);

  // no headline substitution pairs → nothing to explore; hide entirely
  if (subPairs.length === 0) return null;

  const quantile = (q: number) => {
    const idx = Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))));
    return sorted[idx];
  };
  const mean = sorted.reduce((a, b) => a + b, 0) / sorted.length;
  const p10 = quantile(0.1);
  const p90 = quantile(0.9);

  // 20 dots at the 2.5,7.5,…,97.5 percentiles
  const dotVals = Array.from({ length: DOTS }, (_, i) => quantile((i + 0.5) / DOTS));

  const textSummary =
    `At P=${p}%: expected ${money(mean)}; ` +
    `P10–P90 ${money(p10)}–${money(p90)} ` +
    `(floor ${money(floor)}, best estimate ${money(point)}).`;

  return (
    <section className="panel uxp">
      <button
        className="uxp-toggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={`caret ${open ? "open" : ""}`} aria-hidden>
          ▶
        </span>
        <span className="t">Uncertainty explorer</span>
        <span className="hint">what-if sensitivity · secondary</span>
      </button>

      {open && (
        <div className="uxp-body">
          <p className="uxp-frame">
            <b>Illustrative what-if model — not a measured probability.</b> Shows how your total
            recovery moves as you vary the Section-301 assumption (A-21). The engine&apos;s number
            itself is exact for a given assumption.
          </p>

          <div className="uxp-controls">
            <div className="uxp-slider">
              <label className="sl" htmlFor="uxp-p">
                Assume each substituted export independently has a{" "}
                <b className="mono">{p}%</b> chance of bearing Section 301 if imported
              </label>
              <input
                id="uxp-p"
                type="range"
                min={0}
                max={100}
                step={1}
                value={p}
                onChange={(e) => setP(Number(e.target.value))}
                aria-label="Probability each substituted export bears Section 301"
                aria-valuetext={`${p} percent`}
              />
              <div className="ends">
                <button
                  type="button"
                  className="endbtn"
                  onClick={() => {
                    setP(0);
                    setA21("overridden");
                  }}
                >
                  0% = Override
                </button>
                <button
                  type="button"
                  className="endbtn"
                  onClick={() => {
                    setP(100);
                    setA21("confirmed");
                  }}
                >
                  100% = Confirm
                </button>
              </div>
            </div>
          </div>

          <Dotplot
            dots={dotVals}
            mean={mean}
            p10={p10}
            p90={p90}
            floor={floor}
            point={point}
            reduced={reduced}
          />

          <p className="uxp-readout mono">
            <span className="sr">{textSummary}</span>
            <span aria-hidden>
              expected <b>{money(mean)}</b> · P10–P90 {money(p10)}–{money(p90)}
            </span>
          </p>
          <p className="uxp-axisnote">
            Each dot = 5% of outcomes ({DOTS} dots over {TRIALS.toLocaleString()} seeded trials).
            Range spans the conservative floor to the best estimate.
          </p>
        </div>
      )}
    </section>
  );
}

function Dotplot({
  dots,
  mean,
  p10,
  p90,
  floor,
  point,
  reduced,
}: {
  dots: number[];
  mean: number;
  p10: number;
  p90: number;
  floor: number;
  point: number;
  reduced: boolean;
}) {
  const W = 680;
  const H = 150;
  const padL = 14;
  const padR = 14;
  const axisY = H - 30;
  const topPad = 18; // leave room for the "mean" label
  const plotW = W - padL - padR;
  const plotH = axisY - topPad;

  // axis spans floor…point with a hair of padding so edge dots aren't clipped
  const span = Math.max(1, point - floor);
  const lo = floor - span * 0.04;
  const hi = point + span * 0.04;
  const x = (v: number) => padL + ((v - lo) / (hi - lo)) * plotW;

  // First pass: assign each dot to an x-column and find the tallest stack, so
  // the geometry can adapt — with few distinct outcomes the columns get tall,
  // so we shrink the dot radius / vertical step to always fit the plot height.
  const r0 = 7;
  const colW = r0 * 2 + 1.5;
  const counts = new Map<number, number>();
  const cols = dots.map((v) => {
    const col = Math.round(x(v) / colW);
    const idx = counts.get(col) ?? 0;
    counts.set(col, idx + 1);
    return { col, idx, v };
  });
  const maxStack = Math.max(1, ...counts.values());
  // vertical step that fits maxStack dots in plotH; clamp radius to the step
  const step = Math.min(r0 * 2 - 1, (plotH - r0) / maxStack);
  const r = Math.max(3, Math.min(r0, step * 0.62));

  const placed = cols.map(({ col, idx, v }) => ({
    cx: col * colW,
    cy: axisY - r - idx * step,
    v,
  }));

  const ticks = [floor, mean, point];

  return (
    <svg
      className="uxp-svg"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      role="img"
      aria-label={`Quantile dotplot of total recovery: floor ${moneyAbbrev(
        floor,
      )}, mean ${moneyAbbrev(mean)}, best estimate ${moneyAbbrev(
        point,
      )}; P10 to P90 band ${moneyAbbrev(p10)} to ${moneyAbbrev(p90)}.`}
      preserveAspectRatio="xMidYMid meet"
    >
      {/* P10–P90 shaded band */}
      <rect
        className="uxp-band"
        x={x(p10)}
        y={10}
        width={Math.max(1, x(p90) - x(p10))}
        height={axisY - 10}
        rx={3}
      />

      {/* baseline axis */}
      <line className="uxp-axis" x1={padL} y1={axisY} x2={W - padR} y2={axisY} />

      {/* mean marker */}
      <line className="uxp-mean" x1={x(mean)} y1={6} x2={x(mean)} y2={axisY} />
      <text className="uxp-meanlab" x={x(mean)} y={4} textAnchor="middle">
        mean
      </text>

      {/* dots */}
      {placed.map((d, i) => (
        <circle
          key={i}
          className={`uxp-dot ${reduced ? "noanim" : ""}`}
          cx={d.cx}
          cy={d.cy}
          r={r}
        >
          <title>{money(d.v)}</title>
        </circle>
      ))}

      {/* axis tick labels (tabular-num) */}
      {ticks.map((t, i) => (
        <text
          key={i}
          className="uxp-tick"
          x={x(t)}
          y={axisY + 16}
          textAnchor={i === 0 ? "start" : i === ticks.length - 1 ? "end" : "middle"}
        >
          {moneyAbbrev(t)}
        </text>
      ))}
    </svg>
  );
}
