// The work-queue home (BUILD_PLAN §5, M3): totals, triage lanes, the 5-year expiring-value clock,
// and per-client accrued $ — the screen that turns the engine into a daily book-of-business tool.

import { Link } from "react-router-dom";
import { money0, money2, int, prettyDate } from "../../format";
import { api, n } from "../api";
import type { ClaimCard, Lane, LineClock } from "../api";
import { ErrorNote, Money, Spinner, useAsync } from "../ui";

const LANE_STATUS: Record<string, string> = {
  awaiting_signoff: "ready",
  ready_to_file: "ready",
  cbp_rfi: "under_review",
  draft: "draft",
  filed: "filed",
  liquidated: "liquidated",
};

function Tile({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className={`bk-tile${tone ? ` bk-tile-${tone}` : ""}`}>
      <span className="bk-tile-label">{label}</span>
      <span className="bk-tile-value mono">{value}</span>
      {sub && <span className="bk-tile-sub">{sub}</span>}
    </div>
  );
}

function ClaimRow({ c }: { c: ClaimCard }) {
  return (
    <Link to={`/claims/${c.id}`} className="bk-lane-row">
      <span className="bk-lane-row-client">{c.client_name}</span>
      <span className="bk-lane-row-money mono">{money0(n(c.defensible))}</span>
    </Link>
  );
}

function LaneCard({ lane }: { lane: Lane }) {
  const status = LANE_STATUS[lane.key];
  return (
    <div className={`bk-lane bk-lane-${lane.key}`}>
      <header>
        <span className="bk-lane-title">{lane.label}</span>
        <span className="bk-lane-count">{lane.count}</span>
      </header>
      <p className="bk-lane-hint">{lane.hint}</p>
      <div className="bk-lane-total">
        {lane.key === "exceptions" ? "Value at review: " : "Defensible: "}
        <strong className="mono">{money0(n(lane.total_defensible))}</strong>
      </div>
      <div className="bk-lane-rows">
        {lane.preview.length === 0 && <span className="bk-muted">Nothing here — clear lane.</span>}
        {lane.preview.map((c) => (
          <ClaimRow key={c.id} c={c} />
        ))}
      </div>
      {status && lane.count > 0 && (
        <Link className="bk-link bk-lane-all" to={`/claims?status=${status}`}>
          View all {lane.label.toLowerCase()} →
        </Link>
      )}
    </div>
  );
}

const BUCKET_TONE: Record<string, string> = {
  expired: "danger",
  lte_90: "danger",
  lte_180: "warn",
  lte_365: "warn",
  gt_365: "calm",
};

function ClockRow({ lc }: { lc: LineClock }) {
  const overdue = lc.days_remaining < 0;
  return (
    <tr>
      <td className="mono">{lc.entry_number}/{lc.line_no}</td>
      <td>{prettyDate(lc.deadline)}</td>
      <td className={overdue ? "bk-overdue" : undefined}>
        {overdue ? `${Math.abs(lc.days_remaining)}d overdue` : `${int(lc.days_remaining)}d`}
      </td>
      <td className="mono">{int(lc.remaining_qty)}</td>
      <td className="mono">{money2(n(lc.at_risk_duty))}</td>
    </tr>
  );
}

export default function Cockpit() {
  const { data, error, loading, reload } = useAsync(() => api.portfolioSummary(), []);

  if (loading) return <Spinner label="Loading the work queue…" />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return null;

  const { totals, lanes, clock, accrued } = data;

  return (
    <div className="bk-page">
      <div className="bk-page-head">
        <h1>Work queue</h1>
        <span className="bk-muted">as of {prettyDate(data.as_of)}</span>
      </div>

      <div className="bk-tiles">
        <Tile label="Active claims" value={int(totals.active_claims)} sub={`${totals.clients} clients`} />
        <Tile label="Pipeline" value={money0(n(totals.pipeline))} sub="draft + ready (defensible)" />
        <Tile label="In flight" value={money0(n(totals.in_flight))} sub="filed → liquidated" />
        <Tile label="Realized" value={money0(n(totals.realized))} sub="paid" tone="good" />
        <Tile
          label="Expiring duty ⏳"
          value={money0(n(totals.at_risk_duty))}
          sub={`${int(clock.total_lines)} lines on the 5-yr clock`}
          tone="danger"
        />
      </div>

      <h2 className="bk-section">Triage lanes</h2>
      <div className="bk-lanes">
        {lanes.map((lane) => (
          <LaneCard key={lane.key} lane={lane} />
        ))}
      </div>

      <div className="bk-two-col">
        <section className="bk-panel">
          <header className="bk-panel-head">
            <h2>5-year clock — expiring value</h2>
            <span className="bk-muted">19 U.S.C. 1313(r): file within 5 years of import</span>
          </header>
          <div className="bk-clock-buckets">
            {clock.buckets.map((b) => (
              <div key={b.key} className={`bk-bucket bk-bucket-${BUCKET_TONE[b.key] ?? "calm"}`}>
                <span className="bk-bucket-label">{b.label}</span>
                <span className="bk-bucket-value mono">{money0(n(b.at_risk_duty))}</span>
                <span className="bk-bucket-sub">{int(b.lines)} lines</span>
              </div>
            ))}
          </div>
          {clock.soonest.length > 0 && (
            <table className="bk-table bk-clock-table">
              <thead>
                <tr>
                  <th>Entry / line</th>
                  <th>Deadline</th>
                  <th>Time left</th>
                  <th>Undesig. units</th>
                  <th>At-risk duty</th>
                </tr>
              </thead>
              <tbody>
                {clock.soonest.slice(0, 8).map((lc) => (
                  <ClockRow key={lc.import_entry_line_id} lc={lc} />
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="bk-panel">
          <header className="bk-panel-head">
            <h2>Accrued by client</h2>
          </header>
          <table className="bk-table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Claims</th>
                <th>Pipeline</th>
                <th>In flight</th>
                <th>Realized</th>
              </tr>
            </thead>
            <tbody>
              {accrued.map((a) => (
                <tr key={a.client_id}>
                  <td>
                    <Link className="bk-link" to={`/clients/${a.client_id}`}>
                      {a.client_name}
                    </Link>
                  </td>
                  <td className="mono">{a.claims_total}</td>
                  <td><Money value={a.pipeline} /></td>
                  <td><Money value={a.in_flight} /></td>
                  <td><Money value={a.realized} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
