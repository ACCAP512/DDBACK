import { useEffect, useState } from "react";
import { ApiError, api } from "../api";
import type {
  Claim,
  ClaimsResponse,
  LifecycleResponse,
  SignoffRecord,
  SubmitResponse,
} from "../types";
import type { A21State } from "../a21";
import { money2, prettyDate, provisionLabel } from "../format";
import SignoffForm from "./SignoffForm";
import Disclaimer from "./Disclaimer";

interface Props {
  token: string;
  a21: A21State;
}

/**
 * Layer 3 — Filing (SIMULATED). Fetches the generated CATAIR claim(s), shows
 * validation + transmission text, a mock-submit that returns a manifest, and a
 * projected claim lifecycle timeline.
 */
export default function Filing({ token, a21 }: Props) {
  const [claims, setClaims] = useState<ClaimsResponse | null>(null);
  const [life, setLife] = useState<LifecycleResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [manifest, setManifest] = useState<SubmitResponse | null>(null);
  const [submitErr, setSubmitErr] = useState<string | null>(null);

  // Licensed-filer sign-off (COMPLIANCE §4 P3) — gates the mock submit.
  const [signoff, setSignoff] = useState<SignoffRecord | null>(null);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    // a fresh token is a fresh estimate → drop any prior sign-off / manifest.
    setSignoff(null);
    setManifest(null);
    setSubmitErr(null);
    Promise.all([api.claims(token), api.lifecycle(token, true)])
      .then(([c, l]) => {
        if (!live) return;
        setClaims(c);
        setLife(l);
      })
      .catch((e) => {
        if (!live) return;
        setError(
          e instanceof ApiError
            ? `${e.message} (HTTP ${e.status})`
            : e instanceof Error
              ? e.message
              : "Failed to load filing data.",
        );
      })
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [token]);

  async function onSubmit() {
    // Guard client-side too, so the message is instant if somehow unsigned.
    if (!signoff) {
      setSubmitErr("A licensed filer must sign off first — complete the sign-off above.");
      return;
    }
    setSubmitErr(null);
    setSubmitting(true);
    try {
      const res = await api.submit(token);
      setManifest(res);
    } catch (e) {
      // The API returns 428 when no sign-off is recorded yet — translate to the
      // explicit guardrail message regardless of how we got here.
      if (e instanceof ApiError && e.status === 428) {
        setSubmitErr("A licensed filer must sign off first before this claim can be submitted.");
      } else {
        setSubmitErr(e instanceof Error ? e.message : "Mock submit failed.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="center">
        <div>
          <div className="spinner" />
          <div className="muted">Generating CATAIR claims…</div>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="errbox">
        <span className="x">!</span>
        <span>{error}</span>
      </div>
    );
  }
  if (!claims) return null;

  const grand = claims.claims.reduce((a, c) => a + c.totals.grand_total_claimed, 0);

  return (
    <div className="grid" style={{ gap: 22 }}>
      <div className="ribbon">
        <span className="sim">SIMULATED — NOT CONNECTED TO CBP</span>
        <span className="msg">{claims.banner}</span>
      </div>

      <Disclaimer context="export" />

      {/* honest basis line: the server claim is generated on the best-estimate
          (301-on) basis; if A-21 is overridden, flag the divergence. */}
      <div className={`filing-basis ${a21 === "overridden" ? "warn" : ""}`}>
        {a21 === "overridden" ? (
          <>
            <b>Basis note.</b> These claims are generated on the <b>best-estimate (Section-301-on)</b>{" "}
            basis. You overrode A-21 to the conservative floor, so the generated claim above would
            need to be <b>regenerated</b> to match that lower basis before filing.
          </>
        ) : (
          <>
            <b>Basis note.</b> These claims are generated on the <b>best-estimate (Section-301-on)</b>{" "}
            basis (A-21{a21 === "confirmed" ? " confirmed" : " unresolved — headline range"}).
          </>
        )}
      </div>

      <section>
        <div className="panel-head" style={{ marginBottom: 14 }}>
          <h3>
            Generated drawback claims
            <span className="hint" style={{ marginLeft: 10 }}>
              {claims.claims.length} claim(s) · CATAIR (TFTEA)
            </span>
          </h3>
          <span className="mono muted">grand total {money2(grand)}</span>
        </div>

        {claims.claims.map((c, i) => (
          <ClaimCard key={c.claim_number || i} claim={c} />
        ))}
      </section>

      {/* P3 — the mandatory, logged sign-off gate, BEFORE the transmit action. */}
      <SignoffForm token={token} signoff={signoff} onSigned={setSignoff} />

      <section className="panel">
        <div className="panel-head">
          <h3>Transmit</h3>
          <span className="hint">mock submit — writes local files only</span>
        </div>
        <div className="row wrap" style={{ gap: 14 }}>
          <button
            className="btn amber"
            onClick={onSubmit}
            disabled={submitting || !signoff}
            title={signoff ? undefined : "A licensed filer must sign off first"}
          >
            {submitting ? <span className="sp" /> : <PaperIcon />}
            {submitting ? "Submitting (mock)…" : "Mock submit to CBP (simulated)"}
          </button>
          <span className="muted" style={{ fontSize: 12.5, maxWidth: 460 }}>
            {signoff ? (
              <>
                Generates the CATAIR text + JSON artifacts and returns a validation manifest. Nothing
                is transmitted; the recorded sign-off travels with the (simulated) claim.
              </>
            ) : (
              <>
                <b>A licensed filer must sign off first.</b> Complete the sign-off above to enable
                the mock submit.
              </>
            )}
          </span>
        </div>

        {submitErr && (
          <div className="errbox mt16" role="alert">
            <span className="x">!</span>
            <span>{submitErr}</span>
          </div>
        )}

        {manifest && (
          <div className="manifest">
            <div className="mh">
              <CheckBadge />
              Mock submission accepted — {manifest.claims.length} claim(s) packaged
            </div>
            {manifest.signoff && (
              <div className="manifest-signoff">
                <span className="ms-ck" aria-hidden>
                  ✓
                </span>
                <span>
                  Certified by <b>{manifest.signoff.filer_name}</b> ·{" "}
                  {roleShort(manifest.signoff.role)}
                  {manifest.signoff.license_number ? (
                    <> · license <span className="mono">{manifest.signoff.license_number}</span></>
                  ) : null}{" "}
                  · <span className="mono">{prettyTs(manifest.signoff.attested_on)}</span>
                </span>
              </div>
            )}
            {manifest.claims.map((m) => (
              <div className="mrow" key={m.claim_number}>
                <span className="cn">{m.claim_number}</span>
                <span className="muted mono">provision {m.provision}</span>
                <span className="dollar pos">{money2(m.grand_total_claimed)}</span>
                <span className={`valid ${m.valid ? "ok" : "bad"}`}>
                  {m.valid ? "✓ valid" : `✗ ${m.issues.length} issue(s)`}
                </span>
                <span className="files">
                  {m.files.map((f) => (
                    <span className="file" key={f}>
                      {f}
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {life && <Lifecycle life={life} />}
    </div>
  );
}

function ClaimCard({ claim }: { claim: Claim }) {
  const valid = claim.issues.length === 0;
  const accts = Object.entries(claim.totals.by_accounting_class);
  return (
    <div className="claimcard">
      <div className="ch">
        <span className="no">{claim.claim_number}</span>
        <span className="prov">{provisionLabel(claim.drawback_provision_code)}</span>
        <span className={`valid ${valid ? "ok" : "bad"}`}>
          {valid ? "✓ valid" : `✗ ${claim.issues.length} issue(s)`}
        </span>
        {claim.accelerated_payment && (
          <span className="valid ok" title="Accelerated payment requested">
            AP
          </span>
        )}
        <span className="tot">
          <div className="v">{money2(claim.totals.grand_total_claimed)}</div>
          <div className="k">grand total claimed</div>
        </span>
      </div>

      <div className="acctsplit">
        {accts.map(([acct, amt]) => (
          <div className="a" key={acct}>
            <span className="k">acct {acct}</span>
            <span className="v">{money2(amt)}</span>
          </div>
        ))}
        <div className="a">
          <span className="k">ITINs</span>
          <span className="v">
            {claim.imports.length} import / {claim.exports.length} export
          </span>
        </div>
      </div>

      {claim.issues.length > 0 && (
        <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--line)" }}>
          {claim.issues.map((iss, i) => (
            <div key={i} className="mono neg" style={{ fontSize: 12 }}>
              • {iss}
            </div>
          ))}
        </div>
      )}

      <details className="disclose">
        <summary>
          <span className="caret">▶</span>
          View CATAIR transmission text
          <span className="lab">
            {claim.application_identifier} · filer {claim.entry_filer_code} · port {claim.filing_port}
          </span>
        </summary>
        <pre className="wire">{claim.transmission_text}</pre>
      </details>
    </div>
  );
}

function Lifecycle({ life }: { life: LifecycleResponse }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Projected claim lifecycle</h3>
        <span className="hint">
          {life.accelerated_payment ? "accelerated payment" : "no AP"} · simulated dates
        </span>
      </div>

      <div className="lifehead">
        <div className="pill">
          <div className="k">Filing date</div>
          <div className="v">{prettyDate(life.filing_date)}</div>
        </div>
        <div className="pill">
          <div className="k">Current state</div>
          <div className="v">{labelState(life.current_state)}</div>
        </div>
        <div className="pill hi">
          <div className="k">Projected first payment</div>
          <div className="v">{prettyDate(life.projected_first_payment)}</div>
        </div>
        <div className="pill">
          <div className="k">3-yr retention deadline</div>
          <div className="v">{prettyDate(life.retention_deadline)}</div>
        </div>
        <div className="pill">
          <div className="k">Estimated amount</div>
          <div className="v pos">{money2(life.estimated_amount)}</div>
        </div>
      </div>

      <ol className="timeline">
        {life.steps.map((s, i) => {
          const isPay = /paid|payment/i.test(s.state);
          return (
            <li key={i} className={`tstep ${s.status} ${isPay ? "pay" : ""}`}>
              <span className="node" />
              <div className="st">
                <span className="name">{labelState(s.state)}</span>
                <span className="on">{prettyDate(s.on)}</span>
                <span className="badge">{s.status}</span>
              </div>
              <div className="note">{s.note}</div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function roleShort(role: string): string {
  const map: Record<string, string> = {
    licensed_customs_broker: "Licensed customs broker",
    customs_attorney: "Customs attorney",
    self_filer_own_account: "Self-filing importer (own account)",
  };
  return map[role] ?? role.replace(/_/g, " ");
}

function prettyTs(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function labelState(state: string): string {
  const map: Record<string, string> = {
    transmitted: "Transmitted",
    accepted: "Accepted",
    complete: "Docs complete",
    accelerated_payment_paid: "Accelerated payment paid",
    under_review: "Under review",
    liquidated: "Liquidated",
    ap_true_up: "AP true-up",
    paid: "Paid",
  };
  return map[state] ?? state.replace(/_/g, " ");
}

/* icons */
function PaperIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="m22 2-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}
function CheckBadge() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 3 3 5-6" />
    </svg>
  );
}
