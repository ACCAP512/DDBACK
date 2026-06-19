import { useEffect } from "react";
import type { MatchedPair } from "../types";
import {
  chargeLabel,
  daysBetween,
  int,
  money2,
  prettyDate,
  provisionLabel,
} from "../format";

interface Props {
  pair: MatchedPair;
  onClose: () => void;
}

/**
 * The glass-box side panel: "Why this is recoverable". Renders the pair's full
 * TRACE as a numbered derivation with rule citations, assumption chips, the
 * eligible-vs-excluded charge breakdown, the import→export window, an evidence
 * manifest, and the confidence/headline status.
 */
export default function TraceDrawer({ pair, onClose }: Props) {
  const t = pair.trace;

  // close on Escape; lock body scroll while open
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const eligible = Object.entries(t.eligible_charges).filter(([, v]) => v !== 0);
  const excluded = Object.entries(t.excluded_charges);
  const eligibleSum = eligible.reduce((a, [, v]) => a + v, 0);

  const winDays = daysBetween(t.import_date, t.export_date);
  const directId = t.match_basis === "direct_identification";

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Recovery trace">
        <div className="drawer-head">
          <div>
            <div className="t">Why this is recoverable</div>
            <div className="s">
              {pair.import_entry} · line {pair.import_line_no} → {pair.export_reference}
            </div>
          </div>
          <button className="xbtn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="drawer-body">
          {/* headline strip */}
          <div className="tsec">
            <div
              className="row wrap"
              style={{ justifyContent: "space-between", alignItems: "flex-end" }}
            >
              <div>
                <div className="eyebrow" style={{ marginBottom: 6 }}>
                  Line recovery
                </div>
                <div className="dollar pos" style={{ fontSize: 30, fontWeight: 600 }}>
                  {money2(pair.recovery)}
                </div>
                {pair.recovery_low !== pair.recovery && (
                  <div className="muted mono" style={{ fontSize: 12, marginTop: 3 }}>
                    conservative low {money2(pair.recovery_low)}
                  </div>
                )}
              </div>
              <div className="row gap6" style={{ flexWrap: "wrap" }}>
                <span className={`tag ${pair.confidence}`}>
                  <span className="mk" />
                  {pair.confidence} confidence
                </span>
                <span className={`tag ${pair.in_headline ? "high" : "medium"}`}>
                  {pair.in_headline ? "in headline" : "needs review"}
                </span>
              </div>
            </div>
          </div>

          {/* provision */}
          <div className="tsec">
            <div className="th">Provision &amp; match basis</div>
            <div className="cite">{provisionLabel(pair.provision)}</div>
            <div className="muted mono mt8" style={{ fontSize: 12 }}>
              match basis: {t.match_basis.replace(/_/g, " ")}
              {directId ? " · no lesser-of cap" : " · lesser-of comparator applies"}
            </div>
          </div>

          {/* per-unit economics */}
          <div className="tsec">
            <div className="th">Per-unit economics</div>
            <div className="charges">
              <div className="charge">
                <span className="nm">Designated duty / unit</span>
                <span className="amt">{money2(pair.per_unit_designated_duty)}</span>
              </div>
              <div className="charge">
                <span className="nm">Comparator duty / unit</span>
                <span className="amt">
                  {pair.per_unit_comparator_duty == null
                    ? "— (direct-ID)"
                    : money2(pair.per_unit_comparator_duty)}
                </span>
              </div>
              <div className="charge">
                <span className="nm">Recovery / unit (99%)</span>
                <span className="amt pos">{money2(pair.per_unit_recovery)}</span>
              </div>
              <div className="charge">
                <span className="nm">Quantity designated</span>
                <span className="amt">{int(pair.quantity)} units</span>
              </div>
            </div>
          </div>

          {/* numbered derivation */}
          <div className="tsec">
            <div className="th">Computation derivation</div>
            <ol className="deriv">
              {t.computation_steps.map((step, i) => (
                <li key={i}>
                  <span className="n" />
                  <span className="tx" dangerouslySetInnerHTML={{ __html: emphasizeMoney(step) }} />
                </li>
              ))}
            </ol>
          </div>

          {/* eligible vs excluded charges */}
          <div className="tsec">
            <div className="th">Charge breakdown (this designation)</div>
            <div className="charges">
              {eligible.map(([k, v]) => (
                <div className="charge incl" key={k}>
                  <span className="nm">
                    <span className="mk" />
                    {chargeLabel(k)}
                    <span className="faint" style={{ fontSize: 11 }}>
                      eligible
                    </span>
                  </span>
                  <span className="amt">{money2(v)}</span>
                </div>
              ))}
              {excluded.map(([k, why]) => (
                <div className="charge excl" key={k}>
                  <span className="nm">
                    <span className="mk" />
                    {chargeLabel(k)}
                  </span>
                  <span className="why">{why}</span>
                </div>
              ))}
              {!eligible.length && !excluded.length && (
                <div className="charge">
                  <span className="nm muted">No per-charge detail on this pair.</span>
                </div>
              )}
              {eligible.length > 0 && (
                <div className="charge-foot">
                  <span>Eligible duty on designated lot</span>
                  <span>{money2(eligibleSum)}</span>
                </div>
              )}
            </div>
          </div>

          {/* window */}
          <div className="tsec">
            <div className="th">
              Drawback window {t.within_window ? "✓ within 5 years" : "⚠ outside window"}
            </div>
            <div className="window">
              <div className="wnode">
                <div className="k">Import</div>
                <div className="v">{prettyDate(t.import_date)}</div>
              </div>
              <div className="arrow">
                →<span className="d">{winDays != null ? `${int(winDays)}d` : ""}</span>
              </div>
              <div className="wnode">
                <div className="k">Export</div>
                <div className="v">{prettyDate(t.export_date)}</div>
              </div>
              <div className="arrow">
                →<span className="d">claim</span>
              </div>
              <div className="wnode">
                <div className="k">Claim</div>
                <div className="v">{prettyDate(t.claim_date)}</div>
              </div>
            </div>
          </div>

          {/* evidence manifest */}
          <div className="tsec">
            <div className="th">Evidence manifest</div>
            <EvidenceManifest pair={pair} />
          </div>

          {/* citations */}
          <div className="tsec">
            <div className="th">Rule citations</div>
            <div className="cites">
              {t.rule_citations.map((c, i) => (
                <div className="cite" key={i}>
                  {c}
                </div>
              ))}
            </div>
          </div>

          {/* assumptions */}
          <div className="tsec">
            <div className="th">Assumptions applied</div>
            <div className="assumptions">
              {t.assumption_ids.map((a, i) => (
                <span className="achip" key={i}>
                  {a}
                </span>
              ))}
            </div>
          </div>

          {t.flags.length > 0 && (
            <div className="tsec">
              <div className="th">Flags</div>
              <div className="assumptions">
                {t.flags.map((f, i) => (
                  <span className="achip" key={i} style={{ color: "var(--amber)" }}>
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

function EvidenceManifest({ pair }: { pair: MatchedPair }) {
  // Derive what proof supports this pair. A missing-proof pair surfaces as a
  // low-confidence / not-in-headline item; flag the export-proof gap explicitly.
  const t = pair.trace;
  const missingProof =
    !pair.in_headline &&
    (pair.confidence === "low" || t.flags.some((f) => /proof|export/i.test(f)));

  const items: Array<{ have: boolean; t: string; s: string }> = [
    {
      have: true,
      t: "Duty-paid import entry",
      s: `${pair.import_entry} · line ${pair.import_line_no} · ${prettyDate(t.import_date)}`,
    },
    {
      have: !missingProof,
      t: "Proof of export",
      s: missingProof
        ? "needs B/L or AES ITN before filing (19 CFR 190.72)"
        : `${pair.export_reference} · exported ${prettyDate(t.export_date)}`,
    },
    {
      have: t.within_window,
      t: "Within 5-year window",
      s: t.within_window
        ? "import→claim inside 19 USC 1313(r)"
        : "outside the statutory window — unrecoverable",
    },
  ];

  return (
    <div className="evidence">
      {items.map((it, i) => (
        <div className={`ev ${it.have ? "have" : "need"}`} key={i}>
          <span className="ic">{it.have ? "✓" : "!"}</span>
          <span className="tx">
            <span className="t">{it.t}</span>
            <span className="s">{it.s}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

/** Bold any $-amount inside a derivation step. */
function emphasizeMoney(s: string): string {
  const esc = s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc.replace(/(\$[\d,]+(?:\.\d+)?)/g, "<b>$1</b>");
}
