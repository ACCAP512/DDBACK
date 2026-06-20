// Client list + onboarding (BUILD_PLAN §5, M3). Creating a client needs clients:write (admin).

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorNote, Spinner, useAsync } from "../ui";

function NewClientForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [importerId, setImporterId] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createClient({ name: name.trim(), importer_id: importerId.trim(), notes: notes.trim() || undefined });
      setName(""); setImporterId(""); setNotes(""); setOpen(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button className="btn btn-primary" type="button" onClick={() => setOpen(true)}>
        + New client
      </button>
    );
  }
  return (
    <form className="bk-inline-form" onSubmit={submit}>
      <input placeholder="Client name" value={name} onChange={(e) => setName(e.target.value)} required />
      <input placeholder="Importer ID (EIN)" value={importerId} onChange={(e) => setImporterId(e.target.value)} required />
      <input placeholder="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
      <button className="btn" type="button" onClick={() => setOpen(false)}>Cancel</button>
      {error && <span className="bk-error">⚠ {error}</span>}
    </form>
  );
}

export default function Clients() {
  const { can } = useAuth();
  const { data, error, loading, reload } = useAsync(() => api.clients(), []);

  return (
    <div className="bk-page">
      <div className="bk-page-head">
        <h1>Clients</h1>
        {can("clients:write") && <NewClientForm onCreated={reload} />}
      </div>
      {loading && <Spinner />}
      {error && <ErrorNote message={error} onRetry={reload} />}
      {data && (
        <table className="bk-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Importer ID</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr><td colSpan={3} className="bk-muted">No clients yet.</td></tr>
            )}
            {data.map((c) => (
              <tr key={c.id}>
                <td><Link className="bk-link" to={`/clients/${c.id}`}>{c.name}</Link></td>
                <td className="mono">{c.importer_id}</td>
                <td className="bk-muted">{c.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
