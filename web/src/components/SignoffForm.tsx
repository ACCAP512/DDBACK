// Licensed-filer sign-off form (COMPLIANCE §4 P3) — the mandatory, logged human
// attestation that gates finalizing/transmitting a claim. The filer affirmatively
// accepts the matched designations, rules, and figures; recorded with name, role,
// license and timestamp. POSTs to /api/claims/{token}/signoff; surfaces 422
// validation errors. On success it lifts the recorded attestation to the parent
// (Filing), which uses it to enable the mock-submit button.

import { useState } from "react";
import { ApiError, api } from "../api";
import type { FilerRole, SignoffRecord } from "../types";

interface Props {
  token: string;
  signoff: SignoffRecord | null;
  onSigned: (rec: SignoffRecord) => void;
}

const ROLE_OPTIONS: { value: FilerRole; label: string }[] = [
  { value: "licensed_customs_broker", label: "Licensed customs broker" },
  { value: "customs_attorney", label: "Customs attorney" },
  { value: "self_filer_own_account", label: "Self-filing importer — own account" },
];

/** Roles that require a license/identifier on record. */
const LICENSED_ROLES: FilerRole[] = ["licensed_customs_broker", "customs_attorney"];

export default function SignoffForm({ token, signoff, onSigned }: Props) {
  const [name, setName] = useState("");
  const [role, setRole] = useState<FilerRole>("licensed_customs_broker");
  const [license, setLicense] = useState("");
  const [acceptedDefensible, setAcceptedDefensible] = useState(false);
  const [reviewUnderstood, setReviewUnderstood] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsLicense = LICENSED_ROLES.includes(role);

  // Already signed → show the recorded attestation (read-only).
  if (signoff) {
    return <SignoffRecordCard rec={signoff} />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const rec = await api.signoff(token, {
        filer_name: name,
        role,
        license_number: needsLicense ? license : undefined,
        accepted_defensible: acceptedDefensible,
        accepted_review_understood: reviewUnderstood,
      });
      onSigned(rec);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Sign-off failed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel signoff">
      <div className="panel-head">
        <h3>Licensed-filer sign-off</h3>
        <span className="hint">required before transmit (19 CFR 190.6 · CBP HQ H350722)</span>
      </div>

      <p className="signoff-intro">
        The determination must be the filer&apos;s. A licensed U.S. customs broker or attorney — or an
        importer/exporter filing solely on its own account — affirmatively accepts the matched
        designations, rules, and figures before any claim file is final. This is recorded with name,
        role, license and timestamp.
      </p>

      <form className="signoff-form" onSubmit={onSubmit}>
        <div className="sf-grid">
          <label className="sf-field">
            <span className="fieldlab">Filer name</span>
            <input
              className="input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name of the filer of record"
              autoComplete="name"
              required
            />
          </label>

          <label className="sf-field">
            <span className="fieldlab">Role</span>
            <select
              className="select"
              value={role}
              onChange={(e) => setRole(e.target.value as FilerRole)}
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          {needsLicense && (
            <label className="sf-field">
              <span className="fieldlab">License number</span>
              <input
                className="input"
                type="text"
                value={license}
                onChange={(e) => setLicense(e.target.value)}
                placeholder="Customs broker / bar license number"
                required
              />
            </label>
          )}
        </div>

        <label className="sf-check">
          <input
            type="checkbox"
            checked={acceptedDefensible}
            onChange={(e) => setAcceptedDefensible(e.target.checked)}
          />
          <span>
            I have reviewed the matched designations, rules, and figures and{" "}
            <b>accept responsibility for the determination and filing</b>.
          </span>
        </label>

        <label className="sf-check">
          <input
            type="checkbox"
            checked={reviewUnderstood}
            onChange={(e) => setReviewUnderstood(e.target.checked)}
          />
          <span>
            I understand the <b>needs-review</b> items are not in the audit-defensible figure.{" "}
            <span className="faint">(optional)</span>
          </span>
        </label>

        {error && (
          <div className="errbox" role="alert">
            <span className="x">!</span>
            <span>{error}</span>
          </div>
        )}

        <div className="row" style={{ gap: 14 }}>
          <button className="btn primary" type="submit" disabled={submitting}>
            {submitting ? <span className="sp" /> : <PenIcon />}
            {submitting ? "Recording sign-off…" : "Record sign-off"}
          </button>
          <span className="muted" style={{ fontSize: 12 }}>
            Required to enable the mock submit below.
          </span>
        </div>
      </form>
    </section>
  );
}

/** The recorded attestation shown after a successful sign-off. */
function SignoffRecordCard({ rec }: { rec: SignoffRecord }) {
  return (
    <section className="panel signoff signed">
      <div className="panel-head">
        <h3>Licensed-filer sign-off</h3>
        <span className="hint">recorded</span>
      </div>

      <div className="signoff-recorded">
        <div className="sr-badge" aria-hidden>
          <CheckBadge />
        </div>
        <div className="sr-body">
          <div className="sr-head">
            Signed off by <b>{rec.filer_name}</b>
          </div>
          <div className="sr-meta">
            <span className="srm">
              <span className="k">Role</span>
              <span className="v">{roleLabel(rec.role)}</span>
            </span>
            {rec.license_number && (
              <span className="srm">
                <span className="k">License</span>
                <span className="v mono">{rec.license_number}</span>
              </span>
            )}
            <span className="srm">
              <span className="k">Attested</span>
              <span className="v mono">{formatTs(rec.attested_on)}</span>
            </span>
            <span className="srm">
              <span className="k">Accepted figures</span>
              <span className="v">
                {rec.accepted_defensible ? "✓ yes" : "—"}
                {rec.accepted_review_understood ? " · review understood" : ""}
              </span>
            </span>
          </div>
          <p className="sr-statement">“{rec.statement}”</p>
        </div>
      </div>
    </section>
  );
}

function roleLabel(role: FilerRole): string {
  const m = ROLE_OPTIONS.find((o) => o.value === role);
  return m ? m.label : role.replace(/_/g, " ");
}

function formatTs(iso: string): string {
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

function PenIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
    </svg>
  );
}
function CheckBadge() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 3 3 5-6" />
    </svg>
  );
}
