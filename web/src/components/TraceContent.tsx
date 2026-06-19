// The dense, parallel trace views (Level 2). Rendered inside Radix Tabs:
// Computation (default) · Citations · Evidence · Assumptions. Shared by the
// trace drawer and the standalone printable pair page. NO third disclosure
// level — these tabs are the deepest the UI goes.

import * as Tabs from "@radix-ui/react-tabs";
import type { MatchedPair } from "../types";
import { chargeLabel, daysBetween, int, money2, prettyDate } from "../format";
import { cfrRefCount } from "../cite";
import { Citation } from "./ui";

/** Per-unit economics + window dates are always-visible context above the tabs. */
export function TraceEconomics({ pair }: { pair: MatchedPair }) {
  const t = pair.trace;
  const winDays = daysBetween(t.import_date, t.export_date);
  return (
    <>
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
    </>
  );
}

export default function TraceTabs({ pair }: { pair: MatchedPair }) {
  const t = pair.trace;
  const eligible = Object.entries(t.eligible_charges).filter(([, v]) => v !== 0);
  const excluded = Object.entries(t.excluded_charges);
  const eligibleSum = eligible.reduce((a, [, v]) => a + v, 0);
  const cfrN = cfrRefCount(t.rule_citations);

  return (
    <Tabs.Root defaultValue="computation" className="tsec">
      <Tabs.List className="drawer-tabs" aria-label="Trace detail">
        <Tabs.Trigger className="dtab" value="computation">
          Computation
        </Tabs.Trigger>
        <Tabs.Trigger className="dtab" value="citations">
          Citations{cfrN ? ` · ${cfrN}` : ""}
        </Tabs.Trigger>
        <Tabs.Trigger className="dtab" value="evidence">
          Evidence
        </Tabs.Trigger>
        <Tabs.Trigger className="dtab" value="assumptions">
          Assumptions
        </Tabs.Trigger>
      </Tabs.List>

      {/* Computation — numbered derivation + charge breakdown */}
      <Tabs.Content value="computation" style={{ paddingTop: 18 }}>
        <ol className="deriv">
          {t.computation_steps.map((step, i) => (
            <li key={i}>
              <span className="n" />
              <span className="tx" dangerouslySetInnerHTML={{ __html: emphasizeMoney(step) }} />
            </li>
          ))}
        </ol>

        <div className="th" style={{ marginTop: 20 }}>
          Charge breakdown (this designation)
        </div>
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
      </Tabs.Content>

      {/* Citations — live deep links */}
      <Tabs.Content value="citations" style={{ paddingTop: 18 }}>
        <div className="cites">
          {t.rule_citations.map((c, i) => (
            <div className="cite" key={i}>
              <Citation raw={c} />
            </div>
          ))}
          {!t.rule_citations.length && <div className="muted">No citations on this pair.</div>}
        </div>
        <p className="muted" style={{ fontSize: 11.5, marginTop: 10 }}>
          Links open the cited regulation at eCFR / Cornell LII in a new tab.
        </p>
      </Tabs.Content>

      {/* Evidence manifest */}
      <Tabs.Content value="evidence" style={{ paddingTop: 18 }}>
        <EvidenceManifest pair={pair} />
      </Tabs.Content>

      {/* Assumptions + flags */}
      <Tabs.Content value="assumptions" style={{ paddingTop: 18 }}>
        <div className="assumptions">
          {t.assumption_ids.map((a, i) => (
            <span className="achip" key={i}>
              {a}
            </span>
          ))}
          {!t.assumption_ids.length && <div className="muted">No explicit assumptions.</div>}
        </div>
        {t.flags.length > 0 && (
          <>
            <div className="th" style={{ marginTop: 18 }}>
              Flags
            </div>
            <div className="assumptions">
              {t.flags.map((f, i) => (
                <span className="achip" key={i} style={{ color: "var(--amber)" }}>
                  {f}
                </span>
              ))}
            </div>
          </>
        )}
      </Tabs.Content>
    </Tabs.Root>
  );
}

export function EvidenceManifest({ pair }: { pair: MatchedPair }) {
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
export function emphasizeMoney(s: string): string {
  const esc = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc.replace(/(\$[\d,]+(?:\.\d+)?)/g, "<b>$1</b>");
}
