import { useEffect, useState } from "react";
import { api } from "./api";
import type { ConfigSummary, Estimate } from "./types";
import { int } from "./format";
import Banner from "./components/Banner";
import Footer from "./components/Footer";
import Landing from "./components/Landing";
import EstimateView from "./components/EstimateView";
import GlassBox from "./components/GlassBox";
import Filing from "./components/Filing";

type Tab = "estimate" | "glassbox" | "filing";

export default function App() {
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [tab, setTab] = useState<Tab>("estimate");

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
  }

  return (
    <div className="app">
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

          {estimate && (
            <nav className="tabs" role="tablist" aria-label="Layers">
              <button
                className="tab"
                role="tab"
                aria-selected={tab === "estimate"}
                onClick={() => setTab("estimate")}
              >
                Estimate
              </button>
              <button
                className="tab"
                role="tab"
                aria-selected={tab === "glassbox"}
                onClick={() => setTab("glassbox")}
              >
                Glass Box
                <span className="tnum">{int(estimate.summary.total_pair_count)}</span>
              </button>
              <button
                className="tab"
                role="tab"
                aria-selected={tab === "filing"}
                onClick={() => setTab("filing")}
              >
                Filing
                <span className="tnum">sim</span>
              </button>
            </nav>
          )}
        </div>
      </header>

      <main className="main">
        <div className="shell">
          {cfg && <Banner config={cfg} />}

          {!estimate && <Landing onEstimate={onEstimate} />}

          {estimate && tab === "estimate" && <EstimateView est={estimate} />}
          {estimate && tab === "glassbox" && <GlassBox est={estimate} />}
          {estimate && tab === "filing" && <Filing token={estimate.token} />}
        </div>
      </main>

      <Footer version={cfg?.version} asOf={cfg?.as_of} />
    </div>
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
