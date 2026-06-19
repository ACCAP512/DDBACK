// Glass-box trace as a right-side SHEET, built on @radix-ui/react-dialog so we
// get focus-trap, ESC-to-close, focus restore and aria-labelledby for free
// while keeping the app's own visual style. Two disclosure levels only:
//   Level 1 (always visible): recovery + range, confidence→bound action, the
//     import→export→claim date line, and a one-line plain-language basis.
//   Level 2 (TraceContent tabs): computation / citations / evidence / assumptions.

import * as Dialog from "@radix-ui/react-dialog";
import type { MatchedPair } from "../types";
import { money2, prettyDate, provisionLabel } from "../format";
import { confidenceAction, evidenceSummary, pairId, plainBasis } from "../pair";
import { ConfidenceBadge, HeadlineBadge } from "./ui";
import TraceTabs, { TraceEconomics } from "./TraceContent";

interface Props {
  pair: MatchedPair;
  onClose: () => void;
  /** walk the current sorted+filtered list without closing */
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export default function TraceDrawer({ pair, onClose, onPrev, onNext, hasPrev, hasNext }: Props) {
  const t = pair.trace;
  const directId = t.match_basis === "direct_identification";
  const act = confidenceAction(pair);
  const ev = evidenceSummary(pair);

  return (
    <Dialog.Root open onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="scrim" />
        <Dialog.Content
          className="drawer"
          aria-describedby={undefined}
          onOpenAutoFocus={(e) => {
            // keep the page scroll position; focus the panel itself
            e.preventDefault();
            (e.currentTarget as HTMLElement).focus();
          }}
        >
          <div className="drawer-head">
            <div>
              <Dialog.Title className="t">Why this is recoverable</Dialog.Title>
              <div className="s">
                {pair.import_entry} · line {pair.import_line_no} → {pair.export_reference}
              </div>
            </div>
            <div className="drawer-nav">
              {(onPrev || onNext) && (
                <>
                  <button
                    className="iconbtn"
                    onClick={onPrev}
                    disabled={!hasPrev}
                    aria-label="Previous pair"
                    title="Previous pair"
                  >
                    ‹
                  </button>
                  <button
                    className="iconbtn"
                    onClick={onNext}
                    disabled={!hasNext}
                    aria-label="Next pair"
                    title="Next pair"
                  >
                    ›
                  </button>
                </>
              )}
              <Dialog.Close className="iconbtn" aria-label="Close trace">
                ×
              </Dialog.Close>
            </div>
          </div>

          {/* ── Level 1: the gist ─────────────────────────────────────────── */}
          <div className="drawer-l1">
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
                    conservative floor {money2(pair.recovery_low)} — best estimate{" "}
                    {money2(pair.recovery)}
                  </div>
                )}
              </div>
              <div className="row gap6" style={{ flexWrap: "wrap" }}>
                <ConfidenceBadge c={pair.confidence} />
                <HeadlineBadge inHeadline={pair.in_headline} />
              </div>
            </div>

            <div className={`l1-action ${pair.confidence}`}>
              <b>
                {act.label} confidence → {act.action}.
              </b>{" "}
              {pair.in_headline
                ? "Counted in the headline recovery."
                : "Held out of the headline until the gap is closed."}
            </div>

            <div className="l1-basis">{plainBasis(pair)}</div>

            <div className="mono muted" style={{ fontSize: 12 }}>
              {prettyDate(t.import_date)} import → {prettyDate(t.export_date)} export →{" "}
              {prettyDate(t.claim_date)} claim
            </div>

            <div className="row gap6 wrap" style={{ justifyContent: "space-between" }}>
              <div className="cite" style={{ flex: 1, minWidth: 240 }}>
                {provisionLabel(pair.provision)}
                <div className="muted mono mt8" style={{ fontSize: 11.5 }}>
                  match basis: {t.match_basis.replace(/_/g, " ")}
                  {directId ? " · no lesser-of cap" : " · lesser-of comparator applies"}
                </div>
              </div>
            </div>

            <div className="evcount">
              {ev.items} evidence item{ev.items === 1 ? "" : "s"} · {ev.cfr} CFR ref
              {ev.cfr === 1 ? "" : "s"}
            </div>
          </div>

          {/* ── Level 2: parallel dense views in tabs ────────────────────── */}
          <div className="drawer-body">
            <TraceEconomics pair={pair} />
            <TraceTabs pair={pair} />
          </div>

          <div className="drawer-foot">
            <a
              className="openpage"
              href={`#/pair/${encodeURIComponent(pairId(pair))}`}
              onClick={onClose}
            >
              Open as page ↗
            </a>
            <span className="muted" style={{ fontSize: 11.5 }}>
              Standalone, printable full-trace view
            </span>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
