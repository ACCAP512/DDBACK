import { useState } from "react";
import { ApiError, api } from "../api";
import type { Estimate } from "../types";
import ResultsSkeleton from "./ResultsSkeleton";

interface Props {
  onEstimate: (e: Estimate) => void;
}

/**
 * Landing state: the magnet. Either load the committed sample dataset (one
 * click → instant estimate) or upload a client's import + export CSVs.
 */
export default function Landing({ onEstimate }: Props) {
  const [importsFile, setImportsFile] = useState<File | null>(null);
  const [exportsFile, setExportsFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<null | "sample" | "upload">(null);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<Estimate>, which: "sample" | "upload") {
    setError(null);
    setBusy(which);
    try {
      const est = await fn();
      onEstimate(est);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.message}${e.status === 0 ? "" : ` (HTTP ${e.status})`}`
          : e instanceof Error
            ? e.message
            : "Request failed. Is the API running on :8000?";
      setError(msg);
      setBusy(null);
    }
  }

  const canUpload = !!importsFile && !!exportsFile && !busy;

  // While a request is in flight, show a full-screen results skeleton (not just
  // a button spinner) so the wait reads as "the dashboard is loading".
  if (busy) return <ResultsSkeleton />;

  return (
    <div className="landing">
      <div className="lead">
        <span className="eyebrow">Duty-drawback recovery · glass-box</span>
        <h1>
          See what you&apos;re owed —<br />
          <span className="g">down to the matched pair.</span>
        </h1>
        <p className="dek">
          Load your import and export data and get an instant, defensible recovery estimate with a
          conservative range. Every dollar traces back to a specific import↔export match, the rule
          that allows it, and the numbered computation behind it.
        </p>

        <div className="layers">
          <div className="lrow">
            <span className="ln">1</span>
            <div>
              <div className="lt">Instant eligibility</div>
              <div className="ld">
                On-screen recovery estimate, broken down by year, HTS and drawback program — plus
                what&apos;s blocked and what you&apos;d need to file.
              </div>
            </div>
          </div>
          <div className="lrow">
            <span className="ln">2</span>
            <div>
              <div className="lt">Glass box</div>
              <div className="ld">
                Drill from the headline number to individual matched pairs and an explainable TRACE:
                rule citations, assumptions, derivation, eligible vs excluded charges.
              </div>
            </div>
          </div>
          <div className="lrow">
            <span className="ln">3</span>
            <div>
              <div className="lt">Filing (simulated)</div>
              <div className="ld">
                Generated CATAIR claim text, validation status and a projected claim lifecycle —
                clearly marked as not connected to CBP.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="loadcard">
        <h3>Load data</h3>
        <p className="ck">Start with the sample dataset, or bring your own CSVs.</p>

        <div className="actions" style={{ marginTop: 0, marginBottom: 18 }}>
          <button
            className="btn primary"
            onClick={() => run(() => api.sampleEstimate("demo"), "sample")}
            disabled={!!busy}
          >
            {busy === "sample" ? <span className="sp" /> : <BoltIcon />}
            {busy === "sample" ? "Building estimate…" : "Load sample data"}
          </button>
        </div>

        <div className="or">or upload</div>

        <div className="dropzones">
          <FileDrop
            label="Imports CSV"
            hint="CBP 7501 / ACE entry-summary lines"
            file={importsFile}
            onPick={setImportsFile}
            template="/template-imports.csv"
          />
          <FileDrop
            label="Exports CSV"
            hint="EEI / AES or bill-of-lading lines"
            file={exportsFile}
            onPick={setExportsFile}
            template="/template-exports.csv"
          />
        </div>

        <p className="privacy">
          <LockMini />
          <span>
            Processed in your session to compute the estimate — your file isn&apos;t stored.
          </span>
        </p>

        <div className="actions">
          <button
            className="btn ghost"
            disabled={!canUpload}
            onClick={() => run(() => api.uploadEstimate(importsFile!, exportsFile!), "upload")}
          >
            {busy === "upload" ? <span className="sp" /> : <UploadIcon />}
            {busy === "upload" ? "Parsing & estimating…" : "Estimate from uploads"}
          </button>
        </div>

        {error && (
          <div className="errbox mt16">
            <span className="x">!</span>
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function FileDrop({
  label,
  hint,
  file,
  onPick,
  template,
}: {
  label: string;
  hint: string;
  file: File | null;
  onPick: (f: File | null) => void;
  template: string;
}) {
  return (
    <div>
      <label className={`drop ${file ? "set" : ""}`}>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => onPick(e.target.files?.[0] ?? null)}
        />
        <span className="di">{file ? <CheckIcon /> : <CsvIcon />}</span>
        <span className="dl">
          <span className="t">{label}</span>
          <span className="f">{file ? file.name : hint}</span>
        </span>
      </label>
      <a className="droplink" href={template} download>
        <DownloadIcon />
        Download example
      </a>
    </div>
  );
}

/* inline icons (no icon lib) */
function BoltIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
    </svg>
  );
}
function UploadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M12 16V4m0 0 4 4m-4-4-4 4" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  );
}
function CsvIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M6 2h8l4 4v16H6z" />
      <path d="M14 2v4h4" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
      <path d="m5 12 5 5 9-11" />
    </svg>
  );
}
function DownloadIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
      <path d="M4 19h16" />
    </svg>
  );
}
function LockMini() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}
