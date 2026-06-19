interface Props {
  version?: string;
  asOf?: string;
}

/** Compliance guardrail footer — present on every screen. */
export default function Footer({ version, asOf }: Props) {
  return (
    <footer className="footer">
      <div className="shell footer-inner">
        <svg
          className="lock"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          aria-hidden
        >
          <rect x="4" y="11" width="16" height="9" rx="2" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
        <p className="ft">
          <b>Preparation &amp; decision-support only.</b> Not the filer of record; not legal advice.
          A licensed customs broker/filer must certify and transmit (19 CFR 190.6). Eligibility is
          dated and litigation-sensitive — re-verify against current CSMS messages and CIT/Fed. Cir.
          dockets before any real CBP filing.
        </p>
        {(version || asOf) && (
          <span className="ver">
            {asOf ? `as_of ${asOf}` : ""}
            {version ? ` · cfg ${version}` : ""}
          </span>
        )}
      </div>
    </footer>
  );
}
