// Root of the Drawback Broker OS SPA (M3): providers + hash router + the authenticated app shell.
// Hash routing keeps deep links working under the static file mount with no server-side fallback.

import { HashRouter, Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import type { ReactElement } from "react";
import { TooltipProvider } from "../components/ui";
import { useTheme } from "../theme";
import { AuthProvider, RequireAuth, useAuth } from "./auth";
import Login from "./pages/Login";
import Cockpit from "./pages/Cockpit";
import Clients from "./pages/Clients";
import ClientDetail from "./pages/ClientDetail";
import Claims from "./pages/Claims";
import ClaimDetail from "./pages/ClaimDetail";

function Shell() {
  const { me, logout } = useAuth();
  const { theme, toggle } = useTheme();
  return (
    <div className="bk-app">
      <header className="bk-nav">
        <div className="bk-nav-brand">
          <span className="bk-logo" aria-hidden>◆</span>
          <span>Drawback Broker OS</span>
        </div>
        <nav className="bk-nav-links" aria-label="Primary">
          {me?.role !== "client" && (
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
              Cockpit
            </NavLink>
          )}
          <NavLink to="/clients" className={({ isActive }) => (isActive ? "active" : "")}>
            Clients
          </NavLink>
          <NavLink to="/claims" className={({ isActive }) => (isActive ? "active" : "")}>
            Claims
          </NavLink>
        </nav>
        <div className="bk-nav-right">
          <button
            className="bk-icon-btn"
            onClick={toggle}
            type="button"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            title="Toggle theme"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
          {me && <span className={`bk-role bk-role-${me.role}`}>{me.role}</span>}
          <button className="btn" onClick={logout} type="button">
            Sign out
          </button>
        </div>
      </header>
      <main className="bk-main">
        <Outlet />
      </main>
    </div>
  );
}

/** Home route: staff see the cockpit; a read-only client is sent to its own claims (the cockpit is
 *  a cross-client staff view), so Cockpit never even mounts for a client. */
function Home(): ReactElement {
  const { me } = useAuth();
  return me?.role === "client" ? <Navigate to="/claims" replace /> : <Cockpit />;
}

export default function BrokerApp() {
  return (
    <TooltipProvider>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              element={
                <RequireAuth>
                  <Shell />
                </RequireAuth>
              }
            >
              <Route path="/" element={<Home />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/clients/:id" element={<ClientDetail />} />
              <Route path="/claims" element={<Claims />} />
              <Route path="/claims/:id" element={<ClaimDetail />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </TooltipProvider>
  );
}
