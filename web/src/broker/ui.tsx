// Small shared atoms for the Broker OS pages: a data-loading hook (with auto-logout on 401), money
// and date display, claim-status chips, and loading/error notes. Wears the app's existing CSS tokens.

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { money0, money2, prettyDate } from "../format";
import { isAuthError, useAuth } from "./auth";
import { n } from "./api";
import type { ClaimStatus } from "./api";

interface AsyncState<T> {
  data?: T;
  error?: string;
  loading: boolean;
  reload: () => void;
}

/** Run an async loader on mount + when `deps` change; expose {data,error,loading,reload}.
 *  A 401 logs the user out (RequireAuth then bounces to /login). */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const { logout } = useAuth();
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({
    loading: true,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    setState({ loading: true });
    fnRef
      .current()
      .then((d) => live && setState({ data: d, loading: false }))
      .catch((e) => {
        if (!live) return;
        if (isAuthError(e)) logout();
        setState({ error: e?.message ?? String(e), loading: false });
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

/** Money from a decimal string — whole-dollar by default, cents on request. */
export function Money({ value, cents = false }: { value: string | null | undefined; cents?: boolean }) {
  if (value == null) return <span className="bk-muted">—</span>;
  return <span className="mono">{cents ? money2(n(value)) : money0(n(value))}</span>;
}

export function Date_({ iso }: { iso: string | null | undefined }) {
  return <>{iso ? prettyDate(iso) : "—"}</>;
}

// ── claim status chip ─────────────────────────────────────────────────────────
export const STATUS_LABEL: Record<ClaimStatus, string> = {
  draft: "Draft",
  ready: "Ready",
  filed: "Filed",
  under_review: "CBP review",
  liquidated: "Liquidated",
  paid: "Paid",
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <span className={`bk-status bk-status-${status}`} role="img" aria-label={STATUS_LABEL[status]}>
      {STATUS_LABEL[status]}
    </span>
  );
}

export const DRAWBACK_LABEL: Record<string, string> = {
  j1: "1313(j)(1) unused — direct ID",
  j2: "1313(j)(2) unused — substitution",
  a: "1313(a) manufacturing — direct ID",
  b: "1313(b) manufacturing — substitution",
  c: "1313(c) rejected merchandise",
};

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="bk-boot" role="status">{label}</div>;
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bk-error" role="alert">
      <span>⚠ {message}</span>
      {onRetry && (
        <button className="btn" onClick={onRetry} type="button">
          Retry
        </button>
      )}
    </div>
  );
}

/** A titled panel — the basic content container across the pages. */
export function Panel({ title, action, children }: { title?: ReactNode; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="bk-panel">
      {(title || action) && (
        <header className="bk-panel-head">
          {title && <h2>{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
