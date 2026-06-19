import { useMemo, useState } from "react";
import type { Confidence, Estimate, MatchedPair } from "../types";
import { int, money0, money2, provisionShort } from "../format";
import TraceDrawer from "./TraceDrawer";

interface Props {
  est: Estimate;
}

type SortKey = "recovery" | "hts8" | "quantity" | "confidence";
const CONF_RANK: Record<Confidence, number> = { high: 3, medium: 2, low: 1 };
const ROW_CAP = 200; // cap DOM rows; "show more" extends in chunks

export default function GlassBox({ est }: Props) {
  const [hts, setHts] = useState("");
  const [conf, setConf] = useState<"all" | Confidence>("all");
  const [headlineOnly, setHeadlineOnly] = useState(false);
  const [sort, setSort] = useState<SortKey>("recovery");
  const [asc, setAsc] = useState(false);
  const [limit, setLimit] = useState(ROW_CAP);
  const [selected, setSelected] = useState<MatchedPair | null>(null);

  const htsOptions = useMemo(() => {
    const set = new Set(est.matched_pairs.map((p) => p.hts8));
    return Array.from(set).sort();
  }, [est.matched_pairs]);

  const filtered = useMemo(() => {
    let rows = est.matched_pairs;
    if (hts) rows = rows.filter((p) => p.hts8 === hts);
    if (conf !== "all") rows = rows.filter((p) => p.confidence === conf);
    if (headlineOnly) rows = rows.filter((p) => p.in_headline);

    const dir = asc ? 1 : -1;
    rows = [...rows].sort((a, b) => {
      switch (sort) {
        case "hts8":
          return dir * a.hts8.localeCompare(b.hts8);
        case "quantity":
          return dir * (a.quantity - b.quantity);
        case "confidence":
          return dir * (CONF_RANK[a.confidence] - CONF_RANK[b.confidence]);
        default:
          return dir * (a.recovery - b.recovery);
      }
    });
    return rows;
  }, [est.matched_pairs, hts, conf, headlineOnly, sort, asc]);

  const shown = filtered.slice(0, limit);
  const sumShown = filtered.reduce((a, p) => a + p.recovery, 0);

  const toggleSort = (k: SortKey) => {
    if (sort === k) setAsc((v) => !v);
    else {
      setSort(k);
      setAsc(k === "hts8"); // codes default ascending, numbers descending
    }
    setLimit(ROW_CAP);
  };

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Reconciliation est={est} />

      <section className="panel flush">
        <div className="tabletools">
          <span className="fieldlab">HTS8</span>
          <select
            className="select"
            value={hts}
            onChange={(e) => {
              setHts(e.target.value);
              setLimit(ROW_CAP);
            }}
          >
            <option value="">All HTS ({htsOptions.length})</option>
            {htsOptions.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>

          <span className="fieldlab">Confidence</span>
          <select
            className="select"
            value={conf}
            onChange={(e) => {
              setConf(e.target.value as "all" | Confidence);
              setLimit(ROW_CAP);
            }}
          >
            <option value="all">All</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <label className="row gap6" style={{ cursor: "pointer", fontSize: 12.5 }}>
            <input
              type="checkbox"
              checked={headlineOnly}
              onChange={(e) => {
                setHeadlineOnly(e.target.checked);
                setLimit(ROW_CAP);
              }}
            />
            <span className="muted">In headline only</span>
          </label>

          <div className="toolspacer" />
          <span className="mono muted" style={{ fontSize: 12 }}>
            {int(filtered.length)} pairs · Σ {money0(sumShown)}
          </span>
        </div>

        <div className="scrollbody">
          <table className="pairs">
            <thead>
              <tr>
                <th>Import entry / line</th>
                <th>Export ref</th>
                <Th label="HTS8" k="hts8" sort={sort} asc={asc} onSort={toggleSort} />
                <Th label="Qty" k="quantity" sort={sort} asc={asc} onSort={toggleSort} num />
                <th>Provision</th>
                <th className="num">Desig. duty/u</th>
                <th className="num">Comparator/u</th>
                <Th label="Recovery" k="recovery" sort={sort} asc={asc} onSort={toggleSort} num />
                <th className="num">Range low</th>
                <Th
                  label="Conf."
                  k="confidence"
                  sort={sort}
                  asc={asc}
                  onSort={toggleSort}
                />
                <th>In headline</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => {
                const id = `${p.import_entry}-${p.import_line_no}-${p.export_reference}`;
                const active =
                  selected &&
                  selected.import_entry === p.import_entry &&
                  selected.import_line_no === p.import_line_no &&
                  selected.export_reference === p.export_reference;
                return (
                  <tr
                    key={id}
                    className={`${active ? "active" : ""} ${p.in_headline ? "" : "out"}`}
                    onClick={() => setSelected(p)}
                    title="Open trace"
                  >
                    <td className="mono">
                      {p.import_entry}
                      <span className="faint"> /{p.import_line_no}</span>
                    </td>
                    <td className="mono">{p.export_reference}</td>
                    <td className="mono">{p.hts8}</td>
                    <td className="num">{int(p.quantity)}</td>
                    <td className="mono" style={{ color: "var(--ink-2)" }}>
                      {provisionShort(p.provision)}
                    </td>
                    <td className="num">{money2(p.per_unit_designated_duty)}</td>
                    <td className="num faint">
                      {p.per_unit_comparator_duty == null
                        ? "—"
                        : money2(p.per_unit_comparator_duty)}
                    </td>
                    <td className="num pos">{money2(p.recovery)}</td>
                    <td className="num faint">{money2(p.recovery_low)}</td>
                    <td>
                      <span className={`tag ${p.confidence}`}>
                        <span className="mk" />
                        {p.confidence}
                      </span>
                    </td>
                    <td>
                      {p.in_headline ? (
                        <span className="dotcheck">✓</span>
                      ) : (
                        <span className="dotno">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!shown.length && (
                <tr>
                  <td colSpan={11}>
                    <div className="empty">No pairs match these filters.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {filtered.length > limit && (
          <div className="rowmore">
            Showing {int(limit)} of {int(filtered.length)} ·{" "}
            <a
              href="#more"
              onClick={(e) => {
                e.preventDefault();
                setLimit((l) => l + ROW_CAP);
              }}
            >
              show {Math.min(ROW_CAP, filtered.length - limit)} more
            </a>
          </div>
        )}
      </section>

      <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
        Click any row to open its full explainable trace — rule citations, assumptions, the numbered
        derivation, charge breakdown, window dates and evidence manifest.
      </p>

      {selected && <TraceDrawer pair={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Th({
  label,
  k,
  sort,
  asc,
  onSort,
  num,
}: {
  label: string;
  k: SortKey;
  sort: SortKey;
  asc: boolean;
  onSort: (k: SortKey) => void;
  num?: boolean;
}) {
  const active = sort === k;
  return (
    <th className={num ? "num" : ""} onClick={() => onSort(k)}>
      {label}
      {active && <span className="ar">{asc ? "▲" : "▼"}</span>}
    </th>
  );
}

function Reconciliation({ est }: { est: Estimate }) {
  // Verify headline == Σ by-program == Σ by-year == Σ in-headline pairs (to the cent).
  const head = est.headline_point;
  const byProg = est.by_program.reduce((a, b) => a + b.recovery, 0);
  const byYear = est.by_year.reduce((a, b) => a + b.recovery, 0);
  const byPairs = est.matched_pairs
    .filter((p) => p.in_headline)
    .reduce((a, p) => a + p.recovery, 0);

  const eq = (a: number, b: number) => Math.abs(a - b) < 0.5; // within rounding
  const ok = eq(head, byProg) && eq(head, byYear) && eq(head, byPairs);

  return (
    <div className="row wrap" style={{ gap: 12 }}>
      <span className={`recon ${ok ? "" : "bad"}`}>
        <span className="ck">{ok ? "✓" : "≠"}</span>
        Headline = Σ by-program = Σ by-year = Σ headline pairs {ok ? "" : "(mismatch)"}
      </span>
      <span className="mono muted" style={{ fontSize: 12 }}>
        {money2(head)} = {money2(byProg)} = {money2(byYear)} = {money2(byPairs)}
      </span>
    </div>
  );
}
