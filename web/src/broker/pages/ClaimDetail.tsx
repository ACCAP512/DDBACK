// Claim detail with tabs (BUILD_PLAN §5, M3): the persisted claim's estimate / glass-box / ledger /
// audit, plus the lifecycle controls and the licensed-filer sign-off gate. The once-ephemeral engine
// outputs are now durable and navigable — this is where the cockpit's "open a claim" lands.

import { Fragment, useState } from "react";
import { Link, useParams } from "react-router-dom";
import * as Tabs from "@radix-ui/react-tabs";
import { money2, int, prettyDate } from "../../format";
import { api, n } from "../api";
import type { ClaimDetail as Claim, ClaimStatus } from "../api";
import { useAuth } from "../auth";
import { DRAWBACK_LABEL, Date_, ErrorNote, Money, Spinner, StatusBadge, STATUS_LABEL, useAsync } from "../ui";

// ── lifecycle + sign-off (Overview tab) ──────────────────────────────────────
function Lifecycle({ claim, onChanged }: { claim: Claim; onChanged: () => void }) {
  const { can } = useAuth();
  const [claimNumber, setClaimNumber] = useState("");
  const [actual, setActual] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function go(to: ClaimStatus) {
    setBusy(true);
    setError(null);
    try {
      await api.transition(claim.id, {
        to,
        claim_number: to === "filed" && claimNumber ? claimNumber : undefined,
        actual_refund: (to === "liquidated" || to === "paid") && actual ? actual : undefined,
      });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transition failed");
    } finally {
      setBusy(false);
    }
  }

  if (!can("claims:write")) return null;
  const next = claim.allowed_transitions;
  const needsNumber = next.includes("filed");
  const needsActual = next.includes("liquidated") || next.includes("paid");

  return (
    <div className="bk-lifecycle">
      <h3>Advance lifecycle</h3>
      {next.length === 0 ? (
        <span className="bk-muted">This claim is at the end of its lifecycle.</span>
      ) : (
        <>
          {needsNumber && (
            <input className="bk-mini" placeholder="CBP claim # (on filing)" value={claimNumber}
              onChange={(e) => setClaimNumber(e.target.value)} />
          )}
          {needsActual && (
            <input className="bk-mini" placeholder="Actual refund (true-up)" value={actual}
              onChange={(e) => setActual(e.target.value)} />
          )}
          <div className="bk-btn-row">
            {next.map((to) => (
              <button key={to} className="btn" disabled={busy} onClick={() => go(to)} type="button">
                → {STATUS_LABEL[to]}
              </button>
            ))}
          </div>
          {claim.allowed_transitions.includes("filed") && !claim.signoff && (
            <p className="bk-note">A claim must be signed off before it can be filed.</p>
          )}
        </>
      )}
      {error && <div className="bk-error" role="alert">⚠ {error}</div>}
    </div>
  );
}

const FILER_ROLES = [
  ["licensed_customs_broker", "Licensed customs broker"],
  ["customs_attorney", "Customs attorney"],
  ["self_filer_own_account", "Self-filer (own account)"],
];

function SignoffBox({ claim, onChanged }: { claim: Claim; onChanged: () => void }) {
  const { can } = useAuth();
  const [name, setName] = useState("");
  const [role, setRole] = useState("licensed_customs_broker");
  const [license, setLicense] = useState("");
  const [accDef, setAccDef] = useState(false);
  const [accRev, setAccRev] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (claim.signoff) {
    const so = claim.signoff as Record<string, unknown>;
    return (
      <div className="bk-signoff bk-signoff-done">
        <h3>✓ Signed off</h3>
        <p>
          <strong>{String(so.filer_name ?? "")}</strong> — {String(so.role ?? "")}
          {so.license_number ? ` (${String(so.license_number)})` : ""}
        </p>
        {so.attested_on != null && <p className="bk-muted">Attested {prettyDate(String(so.attested_on))}</p>}
      </div>
    );
  }
  if (!can("claims:sign")) {
    return (
      <div className="bk-signoff">
        <h3>Sign-off</h3>
        <p className="bk-muted">Not yet certified. A licensed signer must sign off before filing.</p>
      </div>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.signoff(claim.id, {
        filer_name: name.trim(), role, license_number: license.trim() || undefined,
        accepted_defensible: accDef, accepted_review_understood: accRev,
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-off failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="bk-signoff" onSubmit={submit}>
      <h3>Certify (licensed filer sign-off)</h3>
      <input placeholder="Filer name" value={name} onChange={(e) => setName(e.target.value)} required />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        {FILER_ROLES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <input placeholder="License #" value={license} onChange={(e) => setLicense(e.target.value)} />
      <label className="bk-check">
        <input type="checkbox" checked={accDef} onChange={(e) => setAccDef(e.target.checked)} />
        I accept the defensible figure as the basis for this claim.
      </label>
      <label className="bk-check">
        <input type="checkbox" checked={accRev} onChange={(e) => setAccRev(e.target.checked)} />
        I understand the needs-review items are excluded pending evidence.
      </label>
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Signing…" : "Sign off"}</button>
      {error && <div className="bk-error" role="alert">⚠ {error}</div>}
    </form>
  );
}

function Overview({ claim, onChanged }: { claim: Claim; onChanged: () => void }) {
  const ds = claim.designation_summary;
  return (
    <div className="bk-overview">
      <div className="bk-tiles">
        <div className="bk-tile"><span className="bk-tile-label">Estimated (best)</span><span className="bk-tile-value mono">{money2(n(claim.estimated_refund))}</span></div>
        <div className="bk-tile bk-tile-good"><span className="bk-tile-label">Defensible (VERIFIED-only)</span><span className="bk-tile-value mono">{money2(n(claim.defensible_refund))}</span></div>
        <div className="bk-tile"><span className="bk-tile-label">Actual (true-up)</span><span className="bk-tile-value mono">{claim.actual_refund ? money2(n(claim.actual_refund)) : "—"}</span></div>
      </div>
      <div className="bk-two-col">
        <section className="bk-panel">
          <header className="bk-panel-head"><h2>Claim</h2></header>
          <dl className="bk-defs">
            <dt>Program</dt><dd>{claim.program.name} <span className="bk-muted">({DRAWBACK_LABEL[claim.program.drawback_type] ?? claim.program.drawback_type})</span></dd>
            <dt>Period</dt><dd>{claim.period ?? "—"} · {claim.mode}</dd>
            <dt>Designations</dt><dd>{ds.count} ({ds.in_headline_count} in headline)</dd>
            <dt>Headline (Σ in-headline)</dt><dd className="mono">{money2(n(ds.headline_total))}</dd>
            <dt>CBP claim #</dt><dd className="mono">{claim.claim_number ?? "—"}</dd>
            <dt>Engine config</dt><dd className="mono">{claim.tariff_config_version ?? "—"} · as of <Date_ iso={claim.as_of} /></dd>
            <dt>Filed / Liquidated / Paid</dt><dd><Date_ iso={claim.filed_at} /> · <Date_ iso={claim.liquidated_at} /> · <Date_ iso={claim.paid_at} /></dd>
          </dl>
        </section>
        <section className="bk-panel">
          <header className="bk-panel-head"><h2>Status & sign-off</h2></header>
          <Lifecycle claim={claim} onChanged={onChanged} />
          <SignoffBox claim={claim} onChanged={onChanged} />
        </section>
      </div>
    </div>
  );
}

// ── glass-box / ledger / audit tabs ───────────────────────────────────────────
function GlassBox({ id }: { id: string }) {
  const { data, error, loading, reload } = useAsync(() => api.claimDesignations(id), [id]);
  const [open, setOpen] = useState<string | null>(null);
  if (loading) return <Spinner />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return null;
  return (
    <table className="bk-table">
      <thead>
        <tr>
          <th></th><th>Import entry</th><th>Export ref</th><th>Prov.</th><th>Qty</th>
          <th>Recovery</th><th>Confidence</th><th>Headline</th>
        </tr>
      </thead>
      <tbody>
        {data.designations.length === 0 && <tr><td colSpan={8} className="bk-muted">No designations on this claim.</td></tr>}
        {data.designations.map((d) => (
          <Fragment key={d.id}>
            <tr>
              <td>
                <button className="bk-disclose" type="button" aria-expanded={open === d.id}
                  onClick={() => setOpen(open === d.id ? null : d.id)}>
                  {open === d.id ? "▾" : "▸"}
                </button>
              </td>
              <td className="mono">{d.import_line.entry_number}/{d.import_line.line_no}</td>
              <td className="mono">{d.export_line.reference}</td>
              <td>{d.provision}</td>
              <td className="mono">{int(d.quantity)}</td>
              <td className="mono">{money2(n(d.recovery))}</td>
              <td><span className="bk-conf">{d.confidence}</span></td>
              <td>{d.in_headline ? "✓" : <span className="bk-muted">review</span>}</td>
            </tr>
            {open === d.id && (
              <tr className="bk-trace-row">
                <td colSpan={8}>
                  <div className="bk-trace">
                    <span className="bk-muted">HTS {d.import_line.hts10} imported <Date_ iso={d.import_line.import_date} />
                      {" → "} exported <Date_ iso={d.export_line.export_date} />
                      {d.export_line.itn ? ` · ITN ${d.export_line.itn}` : ""}</span>
                    <pre>{JSON.stringify(d.trace ?? {}, null, 2)}</pre>
                  </div>
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}

function Ledger({ id }: { id: string }) {
  const { data, error, loading, reload } = useAsync(() => api.claimLedger(id), [id]);
  if (loading) return <Spinner />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return null;
  return (
    <>
      <p className="bk-muted">Per import line, summed across <em>all</em> claims (the across-time 1313(v) ledger).</p>
      <table className="bk-table">
        <thead>
          <tr><th>Entry / line</th><th>Available</th><th>Designated</th><th>Remaining</th>
            <th>Avail. duty</th><th>Desig. duty</th><th>Remaining duty</th></tr>
        </thead>
        <tbody>
          {data.lines.map((l) => (
            <tr key={l.import_entry_line_id}>
              <td className="mono">{l.entry_number}/{l.line_no}</td>
              <td className="mono">{int(l.available_qty)}</td>
              <td className="mono">{int(l.designated_qty)}</td>
              <td className="mono">{int(l.remaining_qty)}</td>
              <td><Money value={l.available_duty} cents /></td>
              <td><Money value={l.designated_duty} cents /></td>
              <td><Money value={l.remaining_duty} cents /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function Audit({ id }: { id: string }) {
  const { data, error, loading, reload } = useAsync(() => api.claimAudit(id), [id]);
  if (loading) return <Spinner />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return null;
  return (
    <ul className="bk-audit">
      {data.events.length === 0 && <li className="bk-muted">No audit events.</li>}
      {data.events.map((e, i) => (
        <li key={i}>
          <span className="bk-audit-at">{e.at ? prettyDate(e.at) : "—"}</span>
          <span className="bk-audit-action mono">{e.action}</span>
          {e.detail && <span className="bk-muted bk-audit-detail">{JSON.stringify(e.detail)}</span>}
        </li>
      ))}
    </ul>
  );
}

export default function ClaimDetail() {
  const { id = "" } = useParams();
  const { data, error, loading, reload } = useAsync(() => api.claim(id), [id]);
  const [tab, setTab] = useState("overview");

  if (loading) return <Spinner />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="bk-page">
      <div className="bk-crumbs">
        <Link className="bk-link" to="/claims">Claims</Link> <span>/</span>{" "}
        <Link className="bk-link" to={`/clients/${data.client.id}`}>{data.client.name}</Link>{" "}
        <span>/</span> <span>{data.program.name}</span>
      </div>
      <div className="bk-page-head">
        <h1>{data.client.name} <span className="bk-muted">· {data.period ?? "claim"}</span></h1>
        <StatusBadge status={data.status} />
      </div>

      <Tabs.Root value={tab} onValueChange={setTab}>
        <Tabs.List className="bk-tabs" aria-label="Claim views">
          <Tabs.Trigger className="bk-tab" value="overview">Overview</Tabs.Trigger>
          <Tabs.Trigger className="bk-tab" value="glassbox">Glass-box</Tabs.Trigger>
          <Tabs.Trigger className="bk-tab" value="ledger">Ledger</Tabs.Trigger>
          <Tabs.Trigger className="bk-tab" value="audit">Audit</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="overview"><Overview claim={data} onChanged={reload} /></Tabs.Content>
        <Tabs.Content value="glassbox">{tab === "glassbox" && <GlassBox id={id} />}</Tabs.Content>
        <Tabs.Content value="ledger">{tab === "ledger" && <Ledger id={id} />}</Tabs.Content>
        <Tabs.Content value="audit">{tab === "audit" && <Audit id={id} />}</Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
