// Sign-in page. On success, react-router sends the user back to wherever RequireAuth bounced them
// from (or the cockpit). Seeded demo accounts share the password "drawback".

import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const DEMO = [
  ["admin@northstar.test", "Admin — full access"],
  ["signer@northstar.test", "Signer — can certify"],
  ["prep@northstar.test", "Preparer — builds claims"],
  ["client@northstar.test", "Client — read-only, one importer"],
];

export default function Login() {
  const { me, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname: string } } };
  const [email, setEmail] = useState("admin@northstar.test");
  const [password, setPassword] = useState("drawback");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (me) return <Navigate to="/" replace />;

  const dest = location.state?.from?.pathname ?? "/";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(dest, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bk-login">
      <div className="bk-login-card">
        <div className="bk-login-brand">
          <span className="bk-logo" aria-hidden>◆</span> Drawback Broker OS
        </div>
        <p className="bk-login-sub">Sign in to your book of business.</p>
        <form onSubmit={onSubmit}>
          <label className="bk-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              autoComplete="username"
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="bk-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <div className="bk-error" role="alert">⚠ {error}</div>}
          <button className="btn btn-primary bk-login-btn" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="bk-login-demo">
          <span className="bk-muted">Demo accounts (password “drawback”):</span>
          <ul>
            {DEMO.map(([addr, note]) => (
              <li key={addr}>
                <button
                  type="button"
                  className="bk-link"
                  onClick={() => {
                    setEmail(addr);
                    setPassword("drawback");
                  }}
                >
                  {addr}
                </button>
                <span className="bk-muted"> — {note}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
