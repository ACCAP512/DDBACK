import { lazy, Suspense } from "react";
import type { Estimate } from "../types";
import type { A21State } from "../a21";
import {
  A21_ID,
  effectiveBreakdowns,
  effectiveHeadline,
  effectiveLow,
  headlinePairs,
  isSubstitution301Pair,
  speculative301,
} from "../a21";
import type { AssumptionRegistry } from "../assumptions";
import { int, money2, moneyAbbrev, moneyRange, reasonLabel } from "../format";
import { MoneyTip, Tip } from "./ui";
import CountUp from "./CountUp";
import Splits from "./Splits";
import A21Control from "./A21Control";
import UncertaintyExplorer from "./UncertaintyExplorer";

// Recharts is heavy (d3 dependencies); load the by-year chart on demand so it
// stays out of the initial bundle. A themed skeleton holds the slot meanwhile.
const YearChart = lazy(() => import("./YearChart"));

interface Props {
  est: Estimate;
  registry: AssumptionRegistry;
  a21: A21State;
  setA21: (s: A21State) => void;
}

// Recoverable-with-work vs not-recoverable-as-is partition of blocked_by_reason.
const WORK_REASONS = ["missing_export_proof", "not_liquidated"];
const HARD_REASONS = [
  "unused_import_duty",
  "ineligible_duty_only",
  "out_of_window",
  "other_basket_no_match",
  "no_hts_match",
  "data_quality",
];

export default function EstimateView({ est, registry, a21, setA21 }: Props) {
  // A-21-effective aggregates: identical to the server point basis for
  // range/confirmed; exact recovery_low regroupings for overridden.
  const headline = effectiveHeadline(est, a21);
  const { byYear, byHts, byProgram } = effectiveBreakdowns(est, a21);

  return (
    <div className="grid" style={{ gap: 22 }}>
      <DataQualityBanner est={est} />

      <Hero est={est} a21={a21} />

      <A21Card est={est} registry={registry} a21={a21} setA21={setA21} />

      <UncertaintyExplorer est={est} a21={a21} setA21={setA21} />

      <StatTiles est={est} a21={a21} />

      <div className="grid two" style={{ gridTemplateColumns: "1.35fr 1fr", gap: 18 }}>
        <section className="panel">
          <div className="panel-head">
            <h3>Recovery by import year</h3>
            <span className="hint">defensible headline · {byYear.length} years</span>
          </div>
          <Suspense
            fallback={<div className="skel" style={{ height: 210, borderRadius: 10 }} />}
          >
            <YearChart data={byYear} height={210} emptyText="No matched recovery yet" />
          </Suspense>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h3>By drawback program</h3>
            <span className="hint">19 U.S.C. 1313</span>
          </div>
          <Splits data={byProgram} total={headline} variant="program" />
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <h3>Top HTS by recovery</h3>
          <span className="hint">{byHts.length} codes · headline</span>
        </div>
        <Splits data={byHts.slice(0, 8)} total={headline} variant="hts" />
      </section>

      <BlockedPanel est={est} />

      <div className="grid two" style={{ gridTemplateColumns: "1.2fr 1fr", gap: 18 }}>
        <Checklist items={est.filing_checklist} />
        <DataQuality est={est} />
      </div>

      <Notes notes={est.notes} />
    </div>
  );
}

/** The prominent A-21 correctable card, sat right by the conservatism callout. */
function A21Card({
  est,
  registry,
  a21,
  setA21,
}: {
  est: Estimate;
  registry: AssumptionRegistry;
  a21: A21State;
  setA21: (s: A21State) => void;
}) {
  // Only meaningful when there's speculative 301 to resolve.
  const spec = speculative301(est);
  const subCount = headlinePairs(est).filter(isSubstitution301Pair).length;
  if (spec < 0.5 || subCount === 0) return null;
  return (
    <section className="panel a21-card-wrap">
      <div className="panel-head">
        <h3>Resolve the Section-301 assumption</h3>
        <span className="hint">
          {A21_ID} · {subCount} substitution pair{subCount === 1 ? "" : "s"} ·{" "}
          {moneyAbbrev(spec)} in play
        </span>
      </div>
      <A21Control
        assumption={registry.get(A21_ID)}
        state={a21}
        setState={setA21}
        variant="card"
      />
    </section>
  );
}

function Hero({ est, a21 }: { est: Estimate; a21: A21State }) {
  const s = est.summary;

  // A-21-effective headline + range endpoints (never exceeds headline_point).
  const headline = effectiveHeadline(est, a21);
  const low = effectiveLow(est, a21);
  const point = est.headline_point; // the engine's best estimate — the ceiling
  const lowPct = point > 0 ? (low / point) * 100 : 0;
  const collapsed = a21 !== "range"; // confirmed or overridden → single value

  // Conservatism, positively framed: dollars we deliberately left out + the
  // count of flagged items. "left money out to stay safe" reads as a strength.
  const hardExcluded = sumReasons(est, HARD_REASONS);
  const pending = s.potential_total;
  const excludedTotal = hardExcluded + pending;
  const flaggedCount = est.blocked.length + est.data_quality.issues.length;

  // frequency framing: of every 10 matched line-items, how many are firm?
  const firmPer10 =
    s.total_pair_count > 0 ? Math.round((s.headline_pair_count / s.total_pair_count) * 10) : 0;

  return (
    <section className="hero">
      <div className="kicker">
        <span className="pulse" />
        Instant eligibility · {int(s.headline_pair_count)} defensible matched pairs
      </div>

      <div className="headline">
        <div>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            You&apos;re owed approximately
          </div>
          <Tip label={money2(headline)}>
            <CountUp value={headline} />
          </Tip>
        </div>
        {s.potential_total > 0 && (
          <Tip label={`${money2(s.potential_total)} matched but pending review/proof`}>
            <span className="pending">+{moneyAbbrev(s.potential_total)} pending review</span>
          </Tip>
        )}
      </div>

      <p className="explain">
        <b>Defensible, proof-backed recovery</b> from {int(s.headline_pair_count)} matched
        import↔export pairs.{" "}
        {a21 === "confirmed" ? (
          <>The headline is firm — you confirmed substituted exports are Section-301-eligible (A-21).</>
        ) : a21 === "overridden" ? (
          <>Headline shown at the conservative floor — substituted exports are not Section-301-eligible (A-21).</>
        ) : (
          <>The conservative floor excludes speculative Section 301 from the substitution comparator.</>
        )}
      </p>

      {/* conservatism as the headline feature (positively framed) */}
      {excludedTotal > 0 && (
        <div className="conserv">
          <ShieldIcon />
          <div className="ctext">
            <b>Audit-defensible.</b> We left{" "}
            <Tip label={money2(excludedTotal)}>
              <span className="dollar">{moneyAbbrev(excludedTotal)}</span>
            </Tip>{" "}
            out of this number{flaggedCount > 0 ? <> and flagged <b>{flaggedCount}</b> item{flaggedCount === 1 ? "" : "s"}</> : null}{" "}
            to keep the headline conservative — only firmly-supported dollars are counted.
          </div>
        </div>
      )}

      <div className={`rangebar ${collapsed ? "collapsed" : ""}`}>
        <div
          className="track"
          title={
            collapsed
              ? `Firm at ${money2(headline)} (A-21 ${a21})`
              : `Conservative floor ${money2(low)} → best estimate ${money2(point)}`
          }
        >
          {collapsed ? (
            <div className="fill-low" style={{ width: "100%", borderRadius: 8 }} />
          ) : (
            <>
              <div className="fill-low" style={{ width: `${Math.max(2, lowPct)}%` }} />
              <div
                className="fill-point"
                style={{ left: `${Math.max(2, lowPct)}%`, width: `${Math.max(2, 100 - lowPct)}%` }}
              />
            </>
          )}
        </div>
        {collapsed ? (
          <div className="ticks">
            <div className="t">
              <span className="lab">{a21 === "confirmed" ? "Firm — 301 confirmed" : "Conservative floor"}</span>
              <Tip label={money2(headline)}>
                <span className="val pos">{moneyAbbrev(headline)}</span>
              </Tip>
              <span className="faint" style={{ fontSize: 10.5 }}>
                {a21 === "confirmed"
                  ? "range collapsed — claimant-resolved"
                  : "speculative §301 not claimed"}
              </span>
            </div>
            <div className="t right">
              <span className="lab">Best estimate (301-on)</span>
              <Tip label={money2(point)}>
                <span className="val faint">{moneyAbbrev(point)}</span>
              </Tip>
              <span className="faint" style={{ fontSize: 10.5 }}>
                engine ceiling
              </span>
            </div>
          </div>
        ) : (
          <div className="ticks">
            <div className="t">
              <span className="lab">Conservative floor</span>
              <Tip label={money2(low)}>
                <span className="val">{moneyAbbrev(low)}</span>
              </Tip>
              <span className="faint" style={{ fontSize: 10.5 }}>
                what we&apos;d defend in an audit
              </span>
            </div>
            <div className="t right">
              <span className="lab">Best estimate</span>
              <Tip label={money2(point)}>
                <span className="val pos">{moneyAbbrev(point)}</span>
              </Tip>
              <span className="faint" style={{ fontSize: 10.5 }}>
                on current evidence
              </span>
            </div>
          </div>
        )}
      </div>

      <p className="freq">
        About <b>{firmPer10} of every 10</b> matched line-items are firmly recoverable; the rest are
        pending review or blocked.{" "}
        {collapsed
          ? `Headline ${money2(headline)} (A-21 ${a21 === "confirmed" ? "confirmed" : "overridden"}).`
          : <>Range: {moneyRange(low, point)}.</>}
      </p>

      <div className="herostats">
        <div className="s">
          <span className="v">{int(s.imports)}</span>
          <span className="k">imports parsed</span>
        </div>
        <div className="s">
          <span className="v">{int(s.exports)}</span>
          <span className="k">exports parsed</span>
        </div>
        <div className="s">
          <span className="v">
            {int(s.headline_pair_count)}
            <span className="faint"> / {int(s.total_pair_count)}</span>
          </span>
          <span className="k">pairs in headline</span>
        </div>
        <div className="s">
          <span className="v">
            <MoneyTip value={est.eligible_duty_pool} abbrev={moneyAbbrev(est.eligible_duty_pool)} />
          </span>
          <span className="k">eligible duty pool</span>
        </div>
      </div>
    </section>
  );
}

function StatTiles({ est, a21 }: { est: Estimate; a21: A21State }) {
  const s = est.summary;
  const headline = effectiveHeadline(est, a21);
  const low = effectiveLow(est, a21);
  const captureRate =
    est.eligible_duty_pool > 0 ? (headline / est.eligible_duty_pool) * 100 : 0;
  return (
    <div className="tiles">
      <div className="tile">
        <div className="k">Headline recovery</div>
        <div className="v pos">
          <MoneyTip value={headline} abbrev={moneyAbbrev(headline)} />
        </div>
        <div className="sub">
          {a21 === "confirmed"
            ? "firm · 301 confirmed"
            : a21 === "overridden"
              ? "conservative floor basis"
              : "defensible, proof-backed"}
        </div>
      </div>
      <div className="tile">
        <div className="k">{a21 === "confirmed" ? "Floor (firmed)" : "Conservative floor"}</div>
        <div className="v">
          <MoneyTip value={low} abbrev={moneyAbbrev(low)} />
        </div>
        <div className="sub">
          {a21 === "confirmed" ? "risen to best estimate" : "excl. speculative §301"}
        </div>
      </div>
      <div className="tile">
        <div className="k">Pending review</div>
        <div className="v amberc">
          <MoneyTip value={s.potential_total} abbrev={moneyAbbrev(s.potential_total)} />
        </div>
        <div className="sub">matched, needs work</div>
      </div>
      <div className="tile">
        <div className="k">Capture of duty pool</div>
        <div className="v">{captureRate.toFixed(1)}%</div>
        <div className="sub">
          of <MoneyTip value={est.eligible_duty_pool} abbrev={moneyAbbrev(est.eligible_duty_pool)} />{" "}
          eligible
        </div>
      </div>
    </div>
  );
}

/** Row accounting after upload, elevated (research §2.5 / P2). */
function DataQualityBanner({ est }: { est: Estimate }) {
  const dq = est.data_quality;
  const matched = dq.imports_parsed;
  const total = dq.imports_parsed + dq.imports_dropped;
  const skipped = dq.imports_dropped;
  const errors = dq.issues.filter((i) => i.severity === "error");
  const warnings = dq.issues.filter((i) => i.severity !== "error");
  const clean = skipped === 0 && dq.issues.length === 0;

  return (
    <div className={`dq-banner ${clean ? "ok" : errors.length ? "warn" : warnings.length ? "warn" : "ok"}`}>
      <span className="acct">
        {clean ? "✓ " : ""}
        Matched <span className="n">{int(matched)}</span> of <span className="n">{int(total)}</span>{" "}
        import lines
        {skipped > 0 && (
          <>
            {" · "}
            <span className="n" style={{ color: "var(--warn)" }}>
              {int(skipped)} skipped
            </span>{" "}
            (excluded from this estimate)
          </>
        )}
      </span>
      <span className="muted" style={{ fontSize: 12 }}>
        {int(dq.exports_parsed)} exports parsed
        {dq.exports_dropped > 0 ? ` · ${int(dq.exports_dropped)} dropped` : ""}
      </span>
      {dq.issues.length > 0 && (
        <div className="dq-issues" style={{ flexBasis: "100%" }}>
          {dq.issues.slice(0, 6).map((iss, i) => (
            <div key={i} className={`dq-issue ${iss.severity === "error" ? "error" : "warning"}`}>
              <span className="sev">{iss.severity}</span>
              <span>
                row {iss.row} · {iss.field}: {iss.message}
              </span>
            </div>
          ))}
          {dq.issues.length > 6 && (
            <div className="faint mono" style={{ fontSize: 11.5 }}>
              +{dq.issues.length - 6} more…
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BlockedPanel({ est }: { est: Estimate }) {
  const byReason = est.blocked_by_reason ?? {};
  const work = WORK_REASONS.filter((r) => r in byReason).map((r) => ({ r, amt: byReason[r] }));
  const hard = HARD_REASONS.filter((r) => r in byReason).map((r) => ({ r, amt: byReason[r] }));

  const workSum = work.reduce((a, b) => a + b.amt, 0);
  const hardSum = hard.reduce((a, b) => a + b.amt, 0);

  const detailFor = (r: string): string | null => {
    const hit = est.blocked.find((b) => b.reason === r);
    return hit?.detail ?? null;
  };

  const capeNote = est.filing_checklist.find((c) => /IEEPA/i.test(c));

  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Blocked / not-recoverable</h3>
        <span className="hint">why these dollars aren&apos;t in the headline</span>
      </div>

      <div className="blocked-cols">
        <div className="bgroup work">
          <div className="gh">
            <span className="t">Recoverable with work</span>
            <span className="sum">{money2(workSum)}</span>
          </div>
          <div className="blurb">
            Matched dollars that move into the headline once you close a gap.
          </div>
          {work.length ? (
            work.map(({ r, amt }) => (
              <div className="bitem" key={r}>
                <div className="l">
                  <div className="r amberc">{reasonLabel(r)}</div>
                  <div className="d">{detailFor(r) ?? defaultDetail(r)}</div>
                </div>
                <div className="amt amberc">{money2(amt)}</div>
              </div>
            ))
          ) : (
            <div className="bitem">
              <div className="l">
                <div className="d">Nothing pending — all matched recovery is defensible.</div>
              </div>
            </div>
          )}
        </div>

        <div className="bgroup hard">
          <div className="gh">
            <span className="t">Not recoverable as-is</span>
            <span className="sum">{money2(hardSum)}</span>
          </div>
          <div className="blurb">Diagnostic — duty seen but not claimable on this data.</div>
          {hard.map(({ r, amt }) => (
            <div className={`bitem ${r === "ineligible_duty_only" ? "cape" : ""}`} key={r}>
              <div className="l">
                <div className="r neg">{reasonLabel(r)}</div>
                <div className="d">{detailFor(r) ?? defaultDetail(r)}</div>
              </div>
              <div className="amt neg">{money2(amt)}</div>
            </div>
          ))}
          {capeNote && <div className="capecallout">{capeNote}</div>}
        </div>
      </div>
    </section>
  );
}

function sumReasons(est: Estimate, reasons: string[]): number {
  const byReason = est.blocked_by_reason ?? {};
  return reasons.reduce((a, r) => a + (byReason[r] ?? 0), 0);
}

function defaultDetail(r: string): string {
  const map: Record<string, string> = {
    missing_export_proof: "Need bill of lading or AES ITN to prove the export (19 CFR 190.72).",
    not_liquidated: "Confirm final liquidation of the import entry (19 CFR 190.3(a)).",
    out_of_window: "All matching duty-paid imports fall outside the 5-year window (19 USC 1313(r)).",
    other_basket_no_match: "8-digit 'other' basket with no 10-digit substitution match (A-02).",
    no_hts_match: "No eligible import HTS bucket for this export.",
    unused_import_duty: "Duty-paid imports with no matching export — need exports to claim.",
    ineligible_duty_only: "Only ineligible duty present (Section 232 + an IEEPA/CAPE line).",
    data_quality: "Rows flagged by the parser; resolve before relying on these.",
  };
  return map[r] ?? "";
}

function Checklist({ items }: { items: string[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>What we&apos;d need to file</h3>
        <span className="hint">{items.length} items</span>
      </div>
      <ul className="checklist">
        {items.map((it, i) => (
          <li key={i}>
            <span className="box" />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DataQuality({ est }: { est: Estimate }) {
  const dq = est.data_quality;
  const clean = dq.imports_dropped === 0 && dq.exports_dropped === 0 && dq.issues.length === 0;
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Data quality</h3>
        <span className="hint">{clean ? "clean parse" : `${dq.issues.length} issue(s)`}</span>
      </div>
      <div className="dq">
        <div className="stat">
          <div className="v">{int(dq.imports_parsed)}</div>
          <div className="k">imports parsed</div>
        </div>
        <div className="stat">
          <div className="v">{int(dq.exports_parsed)}</div>
          <div className="k">exports parsed</div>
        </div>
        <div className="stat">
          <div className="v" style={{ color: dq.imports_dropped ? "var(--warn)" : undefined }}>
            {int(dq.imports_dropped)}
          </div>
          <div className="k">imports dropped</div>
        </div>
        <div className="stat">
          <div className="v" style={{ color: dq.exports_dropped ? "var(--warn)" : undefined }}>
            {int(dq.exports_dropped)}
          </div>
          <div className="k">exports dropped</div>
        </div>
      </div>
      {clean ? (
        <p className="mt16 muted" style={{ fontSize: 12.5 }}>
          <span className="dq ok">✓ No parser warnings.</span> Every row was ingested.
        </p>
      ) : (
        <p className="mt16 muted" style={{ fontSize: 12.5 }}>
          {dq.issues.length} parser issue(s) — itemized at the top of this estimate. Skipped rows are
          excluded from the recovery figure.
        </p>
      )}
    </section>
  );
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes.length) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Methodology notes</h3>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        {notes.map((n, i) => (
          <p key={i} className="muted" style={{ fontSize: 12.5, margin: 0, lineHeight: 1.55 }}>
            {n}
          </p>
        ))}
      </div>
    </section>
  );
}

function ShieldIcon() {
  return (
    <svg
      className="shield"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
