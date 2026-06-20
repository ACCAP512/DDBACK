// The single, conspicuous decision-support disclaimer (COMPLIANCE §1.5 / P2).
// Rendered at the top of the estimate, in the claim-export area, and as the body
// of the one-time EULA gate, so the exact words appear everywhere a user could
// over-rely on a figure. Centralized here so the language stays identical.

/** The verbatim disclaimer sentence (COMPLIANCE §1.5). Reused by the EULA gate
 *  so its body and the inline strip never drift apart. */
export const DISCLAIMER_TEXT =
  "Decision-support software — not a customs broker, law firm, or accountant, and not a " +
  "substitute for a licensed customs broker or attorney. Does not transact customs business " +
  "or file with CBP. A licensed filer must independently review and file.";

interface Props {
  /** "estimate" sits under the hero; "export" sits in the claim/filing area. */
  context?: "estimate" | "export";
}

/** Conspicuous, repeated disclaimer line. Colour + icon + text (never icon-only);
 *  uses a neutral, slightly raised treatment so it reads as a standing notice
 *  rather than an error. */
export default function Disclaimer({ context = "estimate" }: Props) {
  return (
    <div className="disclaimer" role="note" aria-label="Decision-support disclaimer">
      <InfoIcon />
      <p className="dtext">
        {context === "export" ? (
          <>
            <b>Not a filing.</b> {DISCLAIMER_TEXT}
          </>
        ) : (
          <>
            <b>Estimate, not a determination.</b> {DISCLAIMER_TEXT}
          </>
        )}
      </p>
    </div>
  );
}

function InfoIcon() {
  return (
    <svg
      className="dicon"
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <circle cx="12" cy="12" r="9.5" />
      <path d="M12 11v5" />
      <circle cx="12" cy="7.6" r="0.4" fill="currentColor" stroke="none" />
      <path d="M12 7.4v.4" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
