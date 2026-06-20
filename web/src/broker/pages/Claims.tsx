// Claim list (BUILD_PLAN §5, M3): filter by status (deep-linkable from the cockpit lanes), paginate,
// and open any claim. The client role automatically sees only its own importer's claims (server-side).

import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { prettyDate } from "../../format";
import { api } from "../api";
import type { ClaimStatus } from "../api";
import { ErrorNote, Money, Spinner, StatusBadge, STATUS_LABEL, useAsync } from "../ui";

const PAGE = 25;
const STATUSES: ClaimStatus[] = ["draft", "ready", "filed", "under_review", "liquidated", "paid"];

export default function Claims() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const clientId = params.get("client_id") ?? "";
  const offset = Math.max(0, Number(params.get("offset") ?? "0") || 0);

  const query = useMemo(
    () => ({ status: status || undefined, client_id: clientId || undefined, limit: PAGE, offset }),
    [status, clientId, offset],
  );
  const { data, error, loading, reload } = useAsync(() => api.claims(query), [status, clientId, offset]);

  function setStatus(s: string) {
    const next = new URLSearchParams(params);
    if (s) next.set("status", s);
    else next.delete("status");
    next.delete("offset");
    setParams(next);
  }
  function setOffset(o: number) {
    const next = new URLSearchParams(params);
    if (o > 0) next.set("offset", String(o));
    else next.delete("offset");
    setParams(next);
  }

  const total = data?.total ?? 0;
  const showing = data?.claims.length ?? 0;

  return (
    <div className="bk-page">
      <div className="bk-page-head">
        <h1>Claims</h1>
        <div className="bk-filters">
          <label className="bk-muted" htmlFor="status-filter">Status</label>
          <select id="status-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABEL[s]}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && <Spinner />}
      {error && <ErrorNote message={error} onRetry={reload} />}
      {data && (
        <>
          <table className="bk-table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Program</th>
                <th>Period</th>
                <th>Status</th>
                <th>Estimated</th>
                <th>Defensible</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {showing === 0 && <tr><td colSpan={7} className="bk-muted">No claims match.</td></tr>}
              {data.claims.map((c) => (
                <tr key={c.id}>
                  <td>{c.client_name}</td>
                  <td><Link className="bk-link" to={`/claims/${c.id}`}>{c.program_name}</Link></td>
                  <td>{c.period ?? "—"}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td><Money value={c.estimated} /></td>
                  <td><Money value={c.defensible} /></td>
                  <td className="bk-muted">{c.updated ? prettyDate(c.updated) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="bk-pager">
            <span className="bk-muted">
              {total === 0 ? "0" : `${offset + 1}–${offset + showing}`} of {total}
            </span>
            <span className="bk-pager-btns">
              <button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} type="button">
                ← Prev
              </button>
              <button className="btn" disabled={offset + showing >= total} onClick={() => setOffset(offset + PAGE)} type="button">
                Next →
              </button>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
