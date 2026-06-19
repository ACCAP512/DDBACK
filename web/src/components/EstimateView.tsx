import type { Estimate } from "../types";
import { int, money0, money2, reasonLabel } from "../format";
import CountUp from "./CountUp";
import BarChart from "./BarChart";
import Splits from "./Splits";

interface Props {
  est: Estimate;
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

export default function EstimateView({ est }: Props) {
  const s = est.summary;
  const lowPct = s.headline_point > 0 ? (s.headline_low / s.headline_point) * 100 : 0;

  return (
    <div className="grid" style={{ gap: 22 }}>
      <Hero est={est} lowPct={lowPct} />

      <StatTiles est={est} />

      <div className="grid two" style={{ gridTemplateColumns: "1.35fr 1fr", gap: 18 }}>
        <section className="panel">
          <div className="panel-head">
            <h3>Recovery by import year</h3>
            <span className="hint">defensible headline · {est.by_year.length} years</span>
          </div>
          <BarChart data={est.by_year} height={210} emptyText="No matched recovery yet" />
        </section>

        <section className="panel">
          <div className="panel-head">
            <h3>By drawback program</h3>
            <span className="hint">19 U.S.C. 1313</span>
          </div>
          <Splits data={est.by_program} total={s.headline_point} variant="program" />
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <h3>Top HTS by recovery</h3>
          <span className="hint">{est.by_hts.length} codes · headline</span>
        </div>
        <Splits data={est.by_hts.slice(0, 8)} total={s.headline_point} variant="hts" />
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

function Hero({ est, lowPct }: { est: Estimate; lowPct: number }) {
  const s = est.summary;
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
          <CountUp value={s.headline_point} />
        </div>
        {s.potential_total > 0 && (
          <span className="pending" title="Matched recovery that needs review/proof before it joins the headline">
            +{money0(s.potential_total)} pending review
          </span>
        )}
      </div>

      <p className="explain">
        <b>Defensible, proof-backed recovery</b> from {int(s.headline_pair_count)} matched
        import↔export pairs. The conservative low end excludes speculative Section 301 from the
        substitution comparator.
      </p>

      <div className="rangebar">
        <div className="track" title={`Low ${money2(est.headline_low)} → Point ${money2(est.headline_point)}`}>
          <div className="fill-low" style={{ width: `${Math.max(2, lowPct)}%` }} />
          <div
            className="fill-point"
            style={{ left: `${Math.max(2, lowPct)}%`, width: `${Math.max(2, 100 - lowPct)}%` }}
          />
        </div>
        <div className="ticks">
          <div className="t">
            <span className="lab">Conservative low</span>
            <span className="val">{money2(est.headline_low)}</span>
          </div>
          <div className="t right">
            <span className="lab">Point estimate</span>
            <span className="val pos">{money2(est.headline_point)}</span>
          </div>
        </div>
      </div>

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
          <span className="v">{money0(est.eligible_duty_pool)}</span>
          <span className="k">eligible duty pool</span>
        </div>
      </div>
    </section>
  );
}

function StatTiles({ est }: { est: Estimate }) {
  const s = est.summary;
  const captureRate =
    est.eligible_duty_pool > 0 ? (s.headline_point / est.eligible_duty_pool) * 100 : 0;
  return (
    <div className="tiles">
      <div className="tile">
        <div className="k">Headline recovery</div>
        <div className="v pos">{money0(s.headline_point)}</div>
        <div className="sub">defensible, proof-backed</div>
      </div>
      <div className="tile">
        <div className="k">Conservative low</div>
        <div className="v">{money0(s.headline_low)}</div>
        <div className="sub">excl. speculative §301</div>
      </div>
      <div className="tile">
        <div className="k">Pending review</div>
        <div className="v amberc">{money0(s.potential_total)}</div>
        <div className="sub">matched, needs work</div>
      </div>
      <div className="tile">
        <div className="k">Capture of duty pool</div>
        <div className="v">{captureRate.toFixed(1)}%</div>
        <div className="sub">of {money0(est.eligible_duty_pool)} eligible</div>
      </div>
    </div>
  );
}

function BlockedPanel({ est }: { est: Estimate }) {
  const byReason = est.blocked_by_reason ?? {};
  const work = WORK_REASONS.filter((r) => r in byReason).map((r) => ({ r, amt: byReason[r] }));
  const hard = HARD_REASONS.filter((r) => r in byReason).map((r) => ({ r, amt: byReason[r] }));

  const workSum = work.reduce((a, b) => a + b.amt, 0);
  const hardSum = hard.reduce((a, b) => a + b.amt, 0);

  // detail strings + the CAPE/IEEPA breakout for ineligible_duty_only
  const detailFor = (r: string): string | null => {
    const hit = est.blocked.find((b) => b.reason === r);
    return hit?.detail ?? null;
  };

  // Pull an IEEPA/CAPE dollar figure out of the checklist note if present.
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
        <div className="mt16" style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {dq.issues.slice(0, 6).map((iss, i) => (
            <div
              key={i}
              className="mono"
              style={{
                fontSize: 11.5,
                color: iss.severity === "error" ? "var(--warn)" : "var(--amber)",
              }}
            >
              [{iss.severity}] row {iss.row} · {iss.field}: {iss.message}
            </div>
          ))}
          {dq.issues.length > 6 && (
            <div className="faint mono" style={{ fontSize: 11.5 }}>
              +{dq.issues.length - 6} more…
            </div>
          )}
        </div>
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
