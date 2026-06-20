// Defensibility report view (COMPLIANCE §4 P6) — the glass-box artifact a
// customs professional validates the answer from, without reading code.
// Renders GET /api/defensibility/{token}:
//   • the three-way split (defensible_headline vs best_estimate vs needs_review)
//     with the headline_basis explainer,
//   • a reconciliation badge (claimed ≤ duty paid, + the caps checked),
//   • a rules-fired table (id · title · tier chip · citations · contributes-to),
//   • the tier_summary counts, and the disclaimer.
// Clean, dense and printable.

import { useEffect, useState } from "react";
import { ApiError, api } from "../api";
import type { DefensibilityReport, DefensibilityRule } from "../types";
import { money2, moneyAbbrev } from "../format";
import { tagMeta } from "../assumptions";
import { Citation, Tip } from "./ui";
import Disclaimer from "./Disclaimer";

interface Props {
  token: string;
}

export default function Defensibility({ token }: Props) {
  const [report, setReport] = useState<DefensibilityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    api
      .defensibility(token)
      .then((r) => live && setReport(r))
      .catch((e) => {
        if (!live) return;
        setError(
          e instanceof ApiError
            ? `${e.message} (HTTP ${e.status})`
            : e instanceof Error
              ? e.message
              : "Failed to load the defensibility report.",
        );
      })
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [token]);

  if (loading) {
    return (
      <div className="center">
        <div>
          <div className="spinner" />
          <div className="muted">Compiling the defensibility report…</div>
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
  if (!report) return null;

  return (
    <div className="grid defrep" style={{ gap: 22 }}>
      <Disclaimer context="export" />

      <SplitHeader report={report} />

      <Reconciliation report={report} />

      <RulesFired rules={report.rules_fired} summary={report.tier_summary} />

      <ClaimLines report={report} />

      <section className="panel defrep-disc">
        <p className="muted" style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6 }}>
          {report.disclaimer}
        </p>
        <p className="faint mono" style={{ margin: "8px 0 0", fontSize: 11 }}>
          report basis as_of {report.as_of}
        </p>
      </section>
    </div>
  );
}

/** The headline three-way split + the structural basis explainer. */
function SplitHeader({ report }: { report: DefensibilityReport }) {
  const def = report.defensible_headline;
  const best = report.best_estimate;
  const review = report.needs_review_total;
  // Shares of the best estimate for the proportion bar (clamped to [0,100]).
  const defPct = best > 0 ? Math.min(100, (def / best) * 100) : 0;

  return (
    <section className="panel defsplit">
      <div className="panel-head">
        <h3>Defensibility report</h3>
        <span className="hint">validate the answer from the trace alone</span>
      </div>

      <div className="defsplit-grid">
        <div className="dcol verified">
          <div className="k">Audit-defensible headline</div>
          <div className="v">
            <Tip label={money2(def)}>
              <span className="dollar">{moneyAbbrev(def)}</span>
            </Tip>
          </div>
          <div className="sub">[VERIFIED] legal rules only — a licensed filer can stand behind this today.</div>
        </div>
        <div className="dcol best">
          <div className="k">Best estimate</div>
          <div className="v">
            <Tip label={money2(best)}>
              <span className="dollar">{moneyAbbrev(best)}</span>
            </Tip>
          </div>
          <div className="sub">Optimistic point — the engine ceiling, before review.</div>
        </div>
        <div className="dcol review">
          <div className="k">Needs review</div>
          <div className="v">
            <Tip label={money2(review)}>
              <span className="dollar">{moneyAbbrev(review)}</span>
            </Tip>
          </div>
          <div className="sub">Claimed dollars resting on a non-VERIFIED legal rule or upside — confirm before filing.</div>
        </div>
      </div>

      {/* defensible share of the best estimate */}
      <div className="defbar" aria-hidden>
        <div className="defbar-fill" style={{ width: `${Math.max(2, defPct)}%` }} />
        <div className="defbar-rest" style={{ left: `${Math.max(2, defPct)}%` }} />
      </div>
      <div className="defbar-legend">
        <span>
          <span className="sw verified" /> Defensible {moneyAbbrev(def)}
        </span>
        <span>
          <span className="sw review" /> + Needs review {moneyAbbrev(review)} ={" "}
          <b>best estimate {moneyAbbrev(best)}</b>
        </span>
      </div>

      <p className="defbasis">{report.headline_basis}</p>
    </section>
  );
}

/** Reconciliation badge: green ✓ when ok (claimed ≤ duty paid), red + violations when not. */
function Reconciliation({ report }: { report: DefensibilityReport }) {
  const r = report.reconciliation;
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>Reconciliation</h3>
        <span className="hint">{r.invariant}</span>
      </div>

      <div className={`recon big ${r.ok ? "" : "bad"}`} role="status">
        <span className="ck" aria-hidden>
          {r.ok ? "✓" : "✗"}
        </span>
        {r.ok ? (
          <span>
            Reconciles — total claimed{" "}
            <Tip label={money2(r.total_claimed)}>
              <span className="dollar">{moneyAbbrev(r.total_claimed)}</span>
            </Tip>{" "}
            ≤ duty paid on claimed entries{" "}
            <Tip label={money2(r.duty_paid_on_claimed)}>
              <span className="dollar">{moneyAbbrev(r.duty_paid_on_claimed)}</span>
            </Tip>
          </span>
        ) : (
          <span>
            Does NOT reconcile — {r.violations.length} violation
            {r.violations.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="recon-caps">
        <div className="rc-lab">Per-pair caps re-derived and checked</div>
        <ul>
          {r.per_pair_caps_checked.map((c) => (
            <li key={c}>
              <span className="ck" aria-hidden>
                ✓
              </span>
              <span className="mono">{c}</span>
            </li>
          ))}
        </ul>
      </div>

      {!r.ok && r.violations.length > 0 && (
        <div className="recon-violations">
          {r.violations.map((v, i) => (
            <div key={i} className="mono neg" style={{ fontSize: 12 }}>
              • {v}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/** Tier chip — colour + icon + label (never colour-only). Reuses the assumption
 *  tag presentation since DefensibilityTier === AssumptionTag. */
function TierChip({ tier }: { tier: DefensibilityRule["tier"] }) {
  const m = tagMeta(tier);
  return (
    <span className={`tagbadge ${m.cls}`} title={m.title} role="img" aria-label={`${m.label} rule`}>
      <span aria-hidden>{m.glyph}</span>
      {m.label}
    </span>
  );
}

function ContribChip({ to }: { to: DefensibilityRule["contributes_to"] }) {
  return to === "defensible" ? (
    <span className="tag high" role="img" aria-label="Contributes to the defensible headline">
      <span aria-hidden>✓</span> Defensible
    </span>
  ) : (
    <span className="tag medium" role="img" aria-label="Contributes to needs-review only">
      <span aria-hidden>◷</span> Review
    </span>
  );
}

function RulesFired({
  rules,
  summary,
}: {
  rules: DefensibilityRule[];
  summary: DefensibilityReport["tier_summary"];
}) {
  // Sort so the VERIFIED-defensible rules — the basis of the headline — lead.
  const order: Record<string, number> = { VERIFIED: 0, INFERRED: 1, GUESS: 2 };
  const sorted = [...rules].sort((a, b) => {
    if (a.contributes_to !== b.contributes_to)
      return a.contributes_to === "defensible" ? -1 : 1;
    if (order[a.tier] !== order[b.tier]) return order[a.tier] - order[b.tier];
    return a.id.localeCompare(b.id);
  });

  return (
    <section className="panel flush">
      <div className="panel-head" style={{ padding: "16px 18px 0" }}>
        <h3>Rules fired</h3>
        <span className="hint">{rules.length} rules · grouped by basis</span>
      </div>

      <div className="tier-summary">
        <TierCount label="Verified" cls="verified" glyph="✓" n={summary.VERIFIED ?? 0} />
        <TierCount label="Inferred" cls="inferred" glyph="◉" n={summary.INFERRED ?? 0} />
        <TierCount label="Guess" cls="guess" glyph="○" n={summary.GUESS ?? 0} />
        <span className="ts-note">
          The defensible headline rests only on <b>Verified</b> legal rules.
        </span>
      </div>

      <div className="rules-scroll">
        <table className="pairs rules-table">
          <thead>
            <tr>
              <th style={{ width: 70 }}>ID</th>
              <th>Rule</th>
              <th style={{ width: 132 }}>Tier</th>
              <th>Citations</th>
              <th style={{ width: 124 }}>Basis</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.id} className={r.contributes_to === "defensible" ? "active" : ""}>
                <td className="mono">{r.id}</td>
                <td>
                  {r.title}
                  {r.upside_only && (
                    <span className="upside-tag" title="Upside-only — routes its delta to review, never gates the floor">
                      upside-only
                    </span>
                  )}
                  {!r.legal && (
                    <span className="upside-tag eng" title="Engineering invariant — does not gate the defensible headline">
                      engineering
                    </span>
                  )}
                </td>
                <td>
                  <TierChip tier={r.tier} />
                </td>
                <td>
                  {r.citations.length ? (
                    <div className="rule-cites">
                      {r.citations.map((c) => (
                        <Citation key={c} raw={c} />
                      ))}
                    </div>
                  ) : (
                    <span className="faint mono" style={{ fontSize: 11.5 }}>
                      —
                    </span>
                  )}
                </td>
                <td>
                  <ContribChip to={r.contributes_to} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TierCount({
  label,
  cls,
  glyph,
  n,
}: {
  label: string;
  cls: string;
  glyph: string;
  n: number;
}) {
  return (
    <span className={`ts-chip ${cls}`}>
      <span className="g" aria-hidden>
        {glyph}
      </span>
      <span className="n mono">{n}</span>
      <span className="l">{label}</span>
    </span>
  );
}

/** Per-claim-line split — the rows that compose the headline, each reconciling
 *  claimed = defensible + needs-review. Dense and printable. */
function ClaimLines({ report }: { report: DefensibilityReport }) {
  const lines = report.claim_lines;
  if (!lines.length) return null;
  return (
    <section className="panel flush">
      <div className="panel-head" style={{ padding: "16px 18px 12px" }}>
        <h3>Claim lines</h3>
        <span className="hint">{lines.length} lines · claimed = defensible + needs-review</span>
      </div>
      <div className="rules-scroll">
        <table className="pairs rules-table">
          <thead>
            <tr>
              <th>Import entry</th>
              <th className="num">Line</th>
              <th>Export ref</th>
              <th style={{ width: 60 }}>Prov</th>
              <th className="num">Claimed</th>
              <th className="num">Defensible</th>
              <th className="num">Needs review</th>
              <th>Basis rules</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={`${l.import_entry}-${l.import_line_no}-${l.export_reference}-${i}`}>
                <td className="mono">{l.import_entry}</td>
                <td className="num">{l.import_line_no}</td>
                <td className="mono">{l.export_reference}</td>
                <td className="mono">{l.provision}</td>
                <td className="num">{money2(l.claimed)}</td>
                <td className="num pos">{money2(l.defensible)}</td>
                <td className="num amberc">{money2(l.needs_review)}</td>
                <td>
                  <span className="basis-rules">
                    {l.basis_rules.map((r) => (
                      <span
                        key={r}
                        className={`achip ${
                          l.blocking_rules.includes(r) ? "blocking" : ""
                        }`}
                        title={
                          l.blocking_rules.includes(r)
                            ? `${r} is not VERIFIED — blocks this line from the defensible headline`
                            : r
                        }
                      >
                        {r}
                      </span>
                    ))}
                    {l.basis_all_verified && l.in_headline && (
                      <span className="achip allok" title="Every basis rule is VERIFIED">
                        all verified
                      </span>
                    )}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
