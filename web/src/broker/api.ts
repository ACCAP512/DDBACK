// Authed fetch client for the Drawback Broker OS API (M3).
//
// One JWT is held in localStorage and attached as a Bearer token to every call. A 401 throws
// ApiError(401) so the AuthProvider can log out. Money arrives as exact decimal strings — kept as
// strings end to end; components convert to Number only at the formatting boundary (display only).

const BASE = "/api";
const TOKEN_KEY = "drawback-broker-token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private-mode: token simply won't persist across reloads */
  }
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      const d = (body as { detail?: unknown })?.detail;
      if (d != null) detail = typeof d === "string" ? d : JSON.stringify(d);
    } catch {
      /* keep status-line detail */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { Accept: "application/json", ...extra };
  const t = getToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

async function get<T>(path: string): Promise<T> {
  return unwrap<T>(await fetch(`${BASE}${path}`, { headers: authHeaders() }));
}

async function post<T>(path: string, payload?: unknown): Promise<T> {
  return unwrap<T>(
    await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: authHeaders(payload === undefined ? {} : { "Content-Type": "application/json" }),
      body: payload === undefined ? undefined : JSON.stringify(payload),
    }),
  );
}

// ── types (mirror the FastAPI responses) ──────────────────────────────────────
export type Role = "admin" | "preparer" | "reviewer" | "signer" | "client";
export type ClaimStatus =
  | "draft" | "ready" | "filed" | "under_review" | "liquidated" | "paid";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: Role;
  tenant_id: string;
}

export interface Me {
  user_id: string;
  tenant_id: string;
  role: Role;
  client_scope_id: string | null;
  permissions: string[];
}

export interface ClaimCard {
  id: string;
  client_id: string;
  client_name: string;
  program_id: string;
  program_name: string;
  drawback_type: string;
  status: ClaimStatus;
  mode: string;
  period: string | null;
  estimated: string | null;
  defensible: string | null;
  actual: string | null;
  gap: string | null;
  signed: boolean;
  filed_at: string | null;
  updated: string | null;
}

export interface Lane {
  key: string;
  label: string;
  hint: string;
  count: number;
  total_defensible: string;
  preview: ClaimCard[];
}

export interface ClockBucket {
  key: string;
  label: string;
  lines: number;
  remaining_units: number;
  at_risk_duty: string;
}

export interface LineClock {
  import_entry_line_id: string;
  client_id: string;
  entry_number: string;
  line_no: number;
  hts10: string;
  import_date: string;
  deadline: string;
  days_remaining: number;
  bucket: string;
  quantity: number;
  designated_qty: number;
  remaining_qty: number;
  eligible_duty_paid: string;
  at_risk_duty: string;
}

export interface ClockRollup {
  as_of: string;
  total_lines: number;
  total_at_risk_duty: string;
  buckets: ClockBucket[];
  soonest: LineClock[];
}

export interface ClientAccrued {
  client_id: string;
  client_name: string;
  importer_id: string;
  claims_total: number;
  pipeline: string;
  in_flight: string;
  realized: string;
}

export interface PortfolioSummary {
  as_of: string;
  totals: {
    clients: number;
    active_claims: number;
    at_risk_duty: string;
    pipeline: string;
    in_flight: string;
    realized: string;
  };
  by_status: Record<ClaimStatus, number>;
  lanes: Lane[];
  clock: ClockRollup;
  accrued: ClientAccrued[];
}

export interface ClientSummary {
  id: string;
  name: string;
  importer_id: string;
  notes: string | null;
}

export interface ProgramSummary {
  id: string;
  name: string;
  drawback_type: string;
  mfg_ruling_ref: string | null;
}

export interface ClientDetail extends ClientSummary {
  programs: ProgramSummary[];
  accrued: { claims_total: number; pipeline: string; in_flight: string; realized: string };
}

export interface Program {
  id: string;
  client_id: string;
  name: string;
  drawback_type: string;
  config: Record<string, unknown>;
  mfg_ruling_ref: string | null;
  claims_by_status?: Record<ClaimStatus, number>;
  claims_total?: number;
}

export interface ClaimListResponse {
  claims: ClaimCard[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClaimDetail {
  id: string;
  status: ClaimStatus;
  mode: string;
  period: string | null;
  client: { id: string; name: string; importer_id: string };
  program: { id: string; name: string; drawback_type: string; mfg_ruling_ref: string | null };
  estimated_refund: string | null;
  defensible_refund: string | null;
  actual_refund: string | null;
  claim_number: string | null;
  signoff: Record<string, unknown> | null;
  tariff_config_version: string | null;
  as_of: string | null;
  filed_at: string | null;
  liquidated_at: string | null;
  paid_at: string | null;
  created: string | null;
  updated: string | null;
  designation_summary: {
    count: number;
    recovery_total: string | null;
    in_headline_count: number;
    headline_total: string | null;
  };
  allowed_transitions: ClaimStatus[];
}

export interface Designation {
  id: string;
  quantity: number;
  provision: string;
  per_unit_recovery: string | null;
  recovery: string | null;
  recovery_low: string | null;
  confidence: string;
  in_headline: boolean;
  import_line: {
    id: string; entry_number: string; line_no: number; hts10: string; import_date: string | null;
  };
  export_line: {
    id: string; reference: string; hts10: string; export_date: string | null; itn: string | null;
  };
  trace: Record<string, unknown> | null;
}

export interface DesignationsResponse {
  claim_id: string;
  designations: Designation[];
  count: number;
}

export interface LedgerLine {
  import_entry_line_id: string;
  entry_number: string;
  line_no: number;
  available_qty: number;
  designated_qty: number;
  remaining_qty: number;
  per_unit_duty: string | null;
  available_duty: string | null;
  designated_duty: string | null;
  remaining_duty: string | null;
}

export interface AuditEvent {
  action: string;
  actor_user_id: string | null;
  at: string | null;
  detail: Record<string, unknown> | null;
}

// ── endpoints ─────────────────────────────────────────────────────────────────
export const api = {
  login: (email: string, password: string) =>
    post<LoginResponse>("/auth/login", { email, password }),
  me: () => get<Me>("/auth/me"),

  portfolioSummary: () => get<PortfolioSummary>("/portfolio/summary"),
  portfolioClock: (limit = 50) => get<ClockRollup>(`/portfolio/clock?limit=${limit}`),

  clients: () => get<ClientSummary[]>("/clients"),
  client: (id: string) => get<ClientDetail>(`/clients/${encodeURIComponent(id)}`),
  createClient: (body: { name: string; importer_id: string; notes?: string }) =>
    post<ClientSummary>("/clients", body),

  programs: (clientId?: string) =>
    get<Program[]>(`/programs${clientId ? `?client_id=${encodeURIComponent(clientId)}` : ""}`),
  createProgram: (body: {
    client_id: string; name: string; drawback_type: string; mfg_ruling_ref?: string;
  }) => post<Program>("/programs", body),

  claims: (params: {
    status?: string; client_id?: string; program_id?: string; limit?: number; offset?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.client_id) q.set("client_id", params.client_id);
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.offset != null) q.set("offset", String(params.offset));
    const qs = q.toString();
    return get<ClaimListResponse>(`/claims${qs ? `?${qs}` : ""}`);
  },
  claim: (id: string) => get<ClaimDetail>(`/claims/${encodeURIComponent(id)}`),
  claimDesignations: (id: string) =>
    get<DesignationsResponse>(`/claims/${encodeURIComponent(id)}/designations`),
  claimLedger: (id: string) =>
    get<{ claim_id: string; lines: LedgerLine[] }>(`/claims/${encodeURIComponent(id)}/ledger`),
  claimAudit: (id: string) =>
    get<{ claim_id: string; events: AuditEvent[] }>(`/claims/${encodeURIComponent(id)}/audit`),
  transition: (id: string, body: { to: string; claim_number?: string; actual_refund?: string }) =>
    post<{ id: string; status: ClaimStatus; allowed_transitions: ClaimStatus[] }>(
      `/claims/${encodeURIComponent(id)}/transition`, body),
  signoff: (
    id: string,
    body: {
      filer_name: string; role: string; license_number?: string;
      accepted_defensible: boolean; accepted_review_understood: boolean;
    },
  ) => post<{ claim_id: string; signoff: Record<string, unknown> }>(
    `/claims/${encodeURIComponent(id)}/signoff`, body),
};

/** Decimal-string → number, for display formatting only (source of truth stays the string). */
export const n = (s: string | null | undefined): number => (s == null ? 0 : Number(s));
