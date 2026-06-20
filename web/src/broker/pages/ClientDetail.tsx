// Client detail (BUILD_PLAN §5, M3): identity, accrued $, programs (+ create), and this client's
// claims. Creating a program needs programs:write (preparer + admin).

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { money0 } from "../../format";
import { api, n } from "../api";
import { useAuth } from "../auth";
import { DRAWBACK_LABEL, ErrorNote, Money, Spinner, StatusBadge, useAsync } from "../ui";

function NewProgramForm({ clientId, onCreated }: { clientId: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("j2");
  const [ruling, setRuling] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createProgram({
        client_id: clientId, name: name.trim(), drawback_type: type,
        mfg_ruling_ref: ruling.trim() || undefined,
      });
      setName(""); setRuling(""); setOpen(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return <button className="btn" type="button" onClick={() => setOpen(true)}>+ New program</button>;
  }
  return (
    <form className="bk-inline-form" onSubmit={submit}>
      <input placeholder="Program name" value={name} onChange={(e) => setName(e.target.value)} required />
      <select value={type} onChange={(e) => setType(e.target.value)}>
        {Object.entries(DRAWBACK_LABEL).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>
      <input placeholder="Mfg ruling ref (optional)" value={ruling} onChange={(e) => setRuling(e.target.value)} />
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
      <button className="btn" type="button" onClick={() => setOpen(false)}>Cancel</button>
      {error && <span className="bk-error">⚠ {error}</span>}
    </form>
  );
}

export default function ClientDetail() {
  const { id = "" } = useParams();
  const { can } = useAuth();
  const client = useAsync(() => api.client(id), [id]);
  const claims = useAsync(() => api.claims({ client_id: id, limit: 100 }), [id]);

  if (client.loading) return <Spinner />;
  if (client.error) return <ErrorNote message={client.error} onRetry={client.reload} />;
  if (!client.data) return null;
  const c = client.data;

  return (
    <div className="bk-page">
      <div className="bk-crumbs">
        <Link className="bk-link" to="/clients">Clients</Link> <span>/</span> <span>{c.name}</span>
      </div>
      <div className="bk-page-head">
        <div>
          <h1>{c.name}</h1>
          <span className="bk-muted mono">Importer {c.importer_id}</span>
          {c.notes && <p className="bk-muted">{c.notes}</p>}
        </div>
      </div>

      <div className="bk-tiles">
        <div className="bk-tile"><span className="bk-tile-label">Claims</span><span className="bk-tile-value mono">{c.accrued.claims_total}</span></div>
        <div className="bk-tile"><span className="bk-tile-label">Pipeline</span><span className="bk-tile-value mono">{money0(n(c.accrued.pipeline))}</span></div>
        <div className="bk-tile"><span className="bk-tile-label">In flight</span><span className="bk-tile-value mono">{money0(n(c.accrued.in_flight))}</span></div>
        <div className="bk-tile bk-tile-good"><span className="bk-tile-label">Realized</span><span className="bk-tile-value mono">{money0(n(c.accrued.realized))}</span></div>
      </div>

      <section className="bk-panel">
        <header className="bk-panel-head">
          <h2>Programs</h2>
          {can("programs:write") && <NewProgramForm clientId={id} onCreated={client.reload} />}
        </header>
        <table className="bk-table">
          <thead><tr><th>Name</th><th>Type</th><th>Mfg ruling</th></tr></thead>
          <tbody>
            {c.programs.length === 0 && <tr><td colSpan={3} className="bk-muted">No programs yet.</td></tr>}
            {c.programs.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{DRAWBACK_LABEL[p.drawback_type] ?? p.drawback_type}</td>
                <td className="bk-muted">{p.mfg_ruling_ref ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bk-panel">
        <header className="bk-panel-head"><h2>Claims</h2></header>
        {claims.loading && <Spinner />}
        {claims.error && <ErrorNote message={claims.error} onRetry={claims.reload} />}
        {claims.data && (
          <table className="bk-table">
            <thead>
              <tr><th>Program</th><th>Period</th><th>Status</th><th>Estimated</th><th>Defensible</th></tr>
            </thead>
            <tbody>
              {claims.data.claims.length === 0 && <tr><td colSpan={5} className="bk-muted">No claims yet.</td></tr>}
              {claims.data.claims.map((cl) => (
                <tr key={cl.id}>
                  <td><Link className="bk-link" to={`/claims/${cl.id}`}>{cl.program_name}</Link></td>
                  <td>{cl.period ?? "—"}</td>
                  <td><StatusBadge status={cl.status} /></td>
                  <td><Money value={cl.estimated} /></td>
                  <td><Money value={cl.defensible} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
