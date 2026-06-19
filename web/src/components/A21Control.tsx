// The Section-301 / A-21 correctable control (Feature 1b). A-21 is the ONE
// assumption a claimant can resolve from their own facts: the origin /
// 301-eligibility of their substituted exported merchandise. The control is a
// GLOBAL three-state setting (range / confirmed / overridden) lifted to App and
// persisted; it sets the same state whether toggled from the prominent card in
// EstimateView or the compact form on the trace Assumptions tab.
//
// Honesty: this resolves an ASSUMPTION from the claimant's own facts — never new
// data. Confirming firms the floor but never raises the headline above
// headline_point.

import type { Assumption } from "../types";
import type { A21State } from "../a21";
import { A21_ID } from "../a21";
import { tagMeta } from "../assumptions";

interface Props {
  /** the A-21 registry entry (carries prompt + effect copy); may be absent */
  assumption?: Assumption;
  state: A21State;
  setState: (s: A21State) => void;
  /** "card" = prominent EstimateView card; "inline" = compact trace-tab form */
  variant: "card" | "inline";
}

// Fallback copy if the registry didn't load (enhancement-only path).
const FALLBACK = {
  prompt:
    "Would the substituted exported merchandise bear Section 301 if it were imported? The lesser-of comparator assumes it would; resolving this from your own facts firms or caps the headline.",
  confirm_label: "Confirm — substituted exports are Section-301-eligible",
  confirm_effect:
    "Resolves the substitution comparator in favor of the best estimate: the conservative floor rises to the point estimate and the headline becomes firm (range collapses).",
  override_label:
    "Override — substituted exports are NOT Section-301-eligible (e.g., domestic origin)",
  override_effect:
    "Caps the substitution comparator without Section 301: the headline drops to the conservative floor; the speculative-301 portion is no longer claimed.",
};

export default function A21Control({ assumption, state, setState, variant }: Props) {
  const c = assumption?.correction ?? FALLBACK;
  const tag = assumption ? tagMeta(assumption.tag) : tagMeta("INFERRED");
  const title = assumption?.title ?? "Comparator rate profile (Section 301)";

  const choose = (next: A21State) => () => setState(state === next ? "range" : next);

  return (
    <div className={`a21 ${variant} state-${state}`}>
      <div className="a21-head">
        <span className={`tagbadge ${tag.cls}`} title={tag.title}>
          <span aria-hidden>{tag.glyph}</span>
          {tag.label}
        </span>
        <span className="a21-id mono">{A21_ID}</span>
        <span className="a21-title">{title}</span>
        <StatePill state={state} />
      </div>

      <p className="a21-prompt">{c.prompt}</p>

      <div className="a21-choices" role="group" aria-label="Resolve the Section-301 assumption">
        <Choice
          active={state === "confirmed"}
          onClick={choose("confirmed")}
          tone="confirm"
          label={c.confirm_label}
          effect={c.confirm_effect}
        />
        <Choice
          active={state === "overridden"}
          onClick={choose("overridden")}
          tone="override"
          label={c.override_label}
          effect={c.override_effect}
        />
        <Choice
          active={state === "range"}
          onClick={() => setState("range")}
          tone="range"
          label="Keep conservative range"
          effect="Leaves A-21 unresolved: the headline keeps showing the conservative floor → best-estimate range, as it does by default."
        />
      </div>

      <p className="a21-note">
        Resolves an assumption from <b>your own facts</b> — not new data. Confirming firms the
        floor; it never raises the headline above the engine&apos;s best estimate.
      </p>
    </div>
  );
}

function Choice({
  active,
  onClick,
  tone,
  label,
  effect,
}: {
  active: boolean;
  onClick: () => void;
  tone: "confirm" | "override" | "range";
  label: string;
  effect: string;
}) {
  return (
    <button
      type="button"
      className={`a21-choice ${tone} ${active ? "active" : ""}`}
      aria-pressed={active}
      onClick={onClick}
    >
      <span className="radio" aria-hidden>
        <span className="dot" />
      </span>
      <span className="ct">
        <span className="lab">{label}</span>
        <span className="eff">{effect}</span>
      </span>
    </button>
  );
}

function StatePill({ state }: { state: A21State }) {
  if (state === "confirmed")
    return <span className="a21-pill firm">Headline firm · 301 confirmed</span>;
  if (state === "overridden")
    return <span className="a21-pill capped">Headline capped · floor basis</span>;
  return <span className="a21-pill range">Showing range</span>;
}
