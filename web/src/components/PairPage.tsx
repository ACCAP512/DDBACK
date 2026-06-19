// Deep-linkable, print-friendly full-trace PAGE for a single pair
// (route #/pair/<id>). Renders the same Level-1 gist + Level-2 detail as the
// drawer, but as a standalone document with a Print / Save PDF action and a
// dedicated print stylesheet. If the estimate isn't loaded at this hash, shows
// a graceful "load data first" message.

import type { Estimate } from "../types";
import type { A21State } from "../a21";
import { effectiveRecovery, isSubstitution301Pair } from "../a21";
import type { AssumptionRegistry } from "../assumptions";
import { money2, prettyDate, provisionLabel } from "../format";
import { confidenceAction, evidenceSummary, findPair, plainBasis } from "../pair";
import { ConfidenceBadge, HeadlineBadge } from "./ui";
import TraceTabs, { TraceEconomics } from "./TraceContent";

interface Props {
  est: Estimate | null;
  id: string;
  onBack: () => void;
  registry: AssumptionRegistry;
  a21: A21State;
  setA21: (s: A21State) => void;
}

export default function PairPage({ est, id, onBack, registry, a21, setA21 }: Props) {
  const pair = est ? findPair(est, id) : undefined;

  if (!est || !pair) {
    return (
      <div className="pairpage">
        <div className="empty" style={{ padding: "60px 0" }}>
          <p style={{ fontSize: 15, color: "var(--ink-1)" }}>
            {est ? "That pair isn’t in the current estimate." : "Load data first."}
          </p>
          <p className="muted" style={{ marginTop: 6 }}>
            This page renders a single matched pair from an in-memory estimate. Run an estimate, then
            reopen this link.
          </p>
          <button className="btn primary mt16" onClick={onBack}>
            ← Back to the app
          </button>
        </div>
      </div>
    );
  }

  const t = pair.trace;
  const directId = t.match_basis === "direct_identification";
  const act = confidenceAction(pair);
  const ev = evidenceSummary(pair);
  const eff = effectiveRecovery(pair, a21);
  const isSub = isSubstitution301Pair(pair);

  return (
    <div className="pairpage">
      <div className="pp-head">
        <div>
          <button className="pp-back no-print" onClick={onBack} style={{ background: "none", border: 0, cursor: "pointer", padding: 0 }}>
            ← Back to the glass box
          </button>
          <h2 style={{ margin: "10px 0 2px", fontSize: 22, letterSpacing: "-0.02em" }}>
            Recovery trace
          </h2>
          <div className="mono muted" style={{ fontSize: 13 }}>
            {pair.import_entry} · line {pair.import_line_no} → {pair.export_reference}
          </div>
        </div>
        <button className="btn ghost no-print" onClick={() => window.print()}>
          <PrintIcon />
          Print / Save PDF
        </button>
      </div>

      {/* Level 1 */}
      <section className="panel" style={{ marginBottom: 18 }}>
        <div className="row wrap" style={{ justifyContent: "space-between", alignItems: "flex-end", gap: 14 }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>
              Line recovery
            </div>
            <div className="dollar pos" style={{ fontSize: 34, fontWeight: 600 }}>
              {money2(eff)}
            </div>
            {isSub && (
              <div className="muted mono" style={{ fontSize: 12.5, marginTop: 4 }}>
                {a21 === "confirmed" ? (
                  <>firmed to best estimate {money2(pair.recovery)} · 301 confirmed (A-21)</>
                ) : a21 === "overridden" ? (
                  <>capped at conservative floor {money2(pair.recovery_low)} · 301 not claimed (A-21)</>
                ) : (
                  <>conservative floor {money2(pair.recovery_low)} — best estimate {money2(pair.recovery)}</>
                )}
              </div>
            )}
          </div>
          <div className="row gap6 wrap">
            <ConfidenceBadge c={pair.confidence} />
            <HeadlineBadge inHeadline={pair.in_headline} />
          </div>
        </div>

        <div className={`l1-action ${pair.confidence}`} style={{ marginTop: 16 }}>
          <b>
            {act.label} confidence → {act.action}.
          </b>{" "}
          {pair.in_headline
            ? "Counted in the headline recovery."
            : "Held out of the headline until the gap is closed."}
        </div>

        <p className="l1-basis" style={{ marginTop: 14 }}>
          {plainBasis(pair)}
        </p>

        <div className="mono muted" style={{ fontSize: 12.5, marginTop: 12 }}>
          {prettyDate(t.import_date)} import → {prettyDate(t.export_date)} export →{" "}
          {prettyDate(t.claim_date)} claim
        </div>

        <div className="cite" style={{ marginTop: 14 }}>
          {provisionLabel(pair.provision)}
          <div className="muted mono mt8" style={{ fontSize: 11.5 }}>
            match basis: {t.match_basis.replace(/_/g, " ")}
            {directId ? " · no lesser-of cap" : " · lesser-of comparator applies"}
          </div>
        </div>

        <div className="evcount" style={{ marginTop: 12 }}>
          {ev.items} evidence item{ev.items === 1 ? "" : "s"} · {ev.cfr} CFR ref
          {ev.cfr === 1 ? "" : "s"}
        </div>
      </section>

      {/* Level 2 */}
      <section className="panel">
        <TraceEconomics pair={pair} />
        <TraceTabs pair={pair} registry={registry} a21={a21} setA21={setA21} />
      </section>

      <p className="muted no-print" style={{ fontSize: 12, marginTop: 16 }}>
        Preparation &amp; decision-support only — not the filer of record; not legal advice.
      </p>
    </div>
  );
}

function PrintIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden>
      <path d="M6 9V3h12v6" />
      <rect x="6" y="13" width="12" height="8" />
      <path d="M6 17H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-2" />
    </svg>
  );
}
