// Tiny fetch client for the Drawback Engine API. All paths are relative to the
// current origin under /api — in dev, Vite proxies /api to http://localhost:8000
// (see vite.config.ts); in prod, FastAPI serves this build from the same origin.

import type {
  ClaimsResponse,
  ConfigSummary,
  Estimate,
  HealthResponse,
  LifecycleResponse,
  SubmitResponse,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        detail = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      try {
        const text = await res.text();
        if (text) detail = text;
      } catch {
        /* keep status-line detail */
      }
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  return unwrap<T>(res);
}

async function postJson<T>(path: string, body?: BodyInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { Accept: "application/json" },
    body,
  });
  return unwrap<T>(res);
}

export const api = {
  health: () => getJson<HealthResponse>("/health"),

  config: () => getJson<ConfigSummary>("/config"),

  sampleEstimate: (scale?: "demo" | string) =>
    postJson<Estimate>(
      `/estimate/sample${scale ? `?scale=${encodeURIComponent(scale)}` : ""}`,
    ),

  uploadEstimate: (imports: File, exports: File) => {
    const form = new FormData();
    form.append("imports", imports);
    form.append("exports", exports);
    return postJson<Estimate>("/estimate/upload", form);
  },

  claims: (token: string) =>
    getJson<ClaimsResponse>(`/claims/${encodeURIComponent(token)}`),

  submit: (token: string) =>
    postJson<SubmitResponse>(`/claims/${encodeURIComponent(token)}/submit`),

  lifecycle: (token: string, acceleratedPayment = true) =>
    getJson<LifecycleResponse>(
      `/lifecycle/${encodeURIComponent(token)}?accelerated_payment=${acceleratedPayment}`,
    ),
};
