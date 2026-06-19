import { useEffect, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { api } from "./api";
import type { ConfigSummary, Estimate } from "./types";
import { int } from "./format";
import { useTheme } from "./theme";
import Banner from "./components/Banner";
import Footer from "./components/Footer";
import Landing from "./components/Landing";
import EstimateView from "./components/EstimateView";
import GlassBox from "./components/GlassBox";
import Filing from "./components/Filing";
import PairPage from "./components/PairPage";
import { TooltipProvider } from "./components/ui";

type Tab = "estimate" | "glassbox" | "filing";

/** Parse the location hash for the standalone pair route (#/pair/<id>). */
function readHash(): string | null {
  const h = window.location.hash;
  const m = h.match(/^#\/pair\/(.+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

export default function App() {
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [tab, setTab] = useState<Tab>("estimate");
  const { theme, toggle } = useTheme();

  // lightweight hash routing for the deep-linkable printable pair page
  const [pairRoute, setPairRoute] = useState<string | null>(() => readHash());
  useEffect(() => {
    const onHash = () => setPairRoute(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Config drives the persistent banner even before any estimate is loaded.
  const [config, setConfig] = useState<ConfigSummary | null>(null);

  useEffect(() => {
    let live = true;
    api
      .config()
      .then((c) => live && setConfig(c))
      .catch(() => {
        /* banner is non-critical; estimate.config also carries it */
      });
    return () => {
      live = false;
    };
  }, []);

  // Prefer the estimate's embedded config once loaded (guaranteed in-sync).
  const cfg = estimate?.config ?? config;

  function onEstimate(e: Estimate) {
    setEstimate(e);
    setTab("estimate");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function reset() {
    setEstimate(null);
    setTab("estimate");
    if (pairRoute) {
      window.location.hash = "";
    }
  }

  function leavePairPage() {
    window.location.hash = "";
    setPairRoute(null);
    setTab("glassbox");
  }

  // Tabbed mode wraps header + main in one Tabs.Root so the tablist and the
  // tabpanels are correctly associated (aria-controls / aria-labelledby, roving
  // tabindex and arrow-key nav all come from Radix). The pair route and the
  // pre-estimate landing render outside the tab machinery.
  const tabbed = !!estimate && !pairRoute;

  const headerActions = (
    <div className="topbar-actions">
      {tabbed && estimate && (
        <Tabs.List className="tabs" aria-label="Layers">
          <Tabs.Trigger className="tab" value="estimate">
            Estimate
          </Tabs.Trigger>
          <Tabs.Trigger className="tab" value="glassbox">
            Glass Box
            <span className="tnum">{int(estimate.summary.total_pair_count)}</span>
          </Tabs.Trigger>
          <Tabs.Trigger className="tab" value="filing">
            Filing
            <span className="tnum">sim</span>
          </Tabs.Trigger>
        </Tabs.List>
      )}
      <ThemeToggle theme={theme} onToggle={toggle} />
    </div>
  );

  const header = (
    <header className="topbar">
      <div className="shell topbar-inner">
        <button
          className="brand"
          onClick={reset}
          style={{ background: "none", border: 0, cursor: "pointer", color: "inherit", padding: 0 }}
          title="Drawback Engine — back to start"
        >
          <Glyph />
          <span>
            <b>Drawback</b> Engine
          </span>
          <span className="sub">duty-drawback eligibility</span>
        </button>
        {headerActions}
      </div>
    </header>
  );

  const body = (
    <main className="main" id="main">
      <div className="shell">
        {pairRoute ? (
          <PairPage est={estimate} id={pairRoute} onBack={leavePairPage} />
        ) : !estimate ? (
          <>
            {cfg && <Banner config={cfg} />}
            <Landing onEstimate={onEstimate} />
          </>
        ) : (
          <>
            {cfg && <Banner config={cfg} />}
            <Tabs.Content value="estimate">
              <EstimateView est={estimate} />
            </Tabs.Content>
            <Tabs.Content value="glassbox">
              <GlassBox est={estimate} />
            </Tabs.Content>
            <Tabs.Content value="filing">
              <Filing token={estimate.token} />
            </Tabs.Content>
          </>
        )}
      </div>
    </main>
  );

  const footer = <Footer version={cfg?.version} asOf={cfg?.as_of} />;

  return (
    <TooltipProvider>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      {tabbed ? (
        // Tabs.Root becomes the .app flex column so header + tabpanels + footer
        // are all inside one tab context with correct ARIA associations.
        <Tabs.Root className="app" value={tab} onValueChange={(v) => setTab(v as Tab)}>
          {header}
          {body}
          {footer}
        </Tabs.Root>
      ) : (
        <div className="app">
          {header}
          {body}
          {footer}
        </div>
      )}
    </TooltipProvider>
  );
}

function ThemeToggle({ theme, onToggle }: { theme: "light" | "dark"; onToggle: () => void }) {
  const dark = theme === "dark";
  return (
    <button
      className="iconbtn"
      onClick={onToggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
    >
      {dark ? (
        // sun
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8 6 18M18 6l1.8-1.8" />
        </svg>
      ) : (
        // moon
        <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M21 12.8A8.5 8.5 0 0 1 11.2 3a7 7 0 1 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  );
}

function Glyph() {
  // Abstract "recovery funnel" mark.
  return (
    <svg className="glyph" viewBox="0 0 32 32" fill="none" aria-hidden>
      <rect x="1" y="1" width="30" height="30" rx="8" fill="var(--accent-wash)" stroke="var(--accent-dim)" />
      <path d="M8 10h16l-6 7v6l-4-2v-4z" fill="var(--accent)" />
      <circle cx="16" cy="9" r="1.4" fill="var(--accent-bright)" />
    </svg>
  );
}
