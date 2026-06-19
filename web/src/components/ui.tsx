// Shared, accessible UI atoms built on Radix primitives but wearing the app's
// own CSS. Centralized so every money figure / status chip behaves identically.

import type { ReactNode } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { Confidence } from "../types";
import { money2 } from "../format";
import { parseCitation } from "../cite";

/** App-wide tooltip provider (mount once near the root). */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <Tooltip.Provider delayDuration={150} skipDelayDuration={300}>
      {children}
    </Tooltip.Provider>
  );
}

/**
 * Wrap an abbreviated figure (e.g. "$3.79M") so hover/focus reveals the full
 * precision (e.g. "$3,787,133.61"). Keyboard-focusable for AT.
 */
export function Tip({
  label,
  children,
  mono = true,
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <span className="tiptrigger" tabIndex={0}>
          {children}
        </span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tipcontent" sideOffset={6} collisionPadding={8}>
          <span className={mono ? "mono" : undefined}>{label}</span>
          <Tooltip.Arrow className="tiparrow" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

/** Abbreviated money with a tooltip carrying the exact value. */
export function MoneyTip({ value, abbrev }: { value: number; abbrev: string }) {
  return (
    <Tip label={money2(value)}>
      <span className="dollar">{abbrev}</span>
    </Tip>
  );
}

// ── status: never colour-only — colour + icon + text label (research §2.2) ───

const CONF_META: Record<Confidence, { label: string; icon: string; action: string }> = {
  high: { label: "High", icon: "●", action: "include in claim" },
  medium: { label: "Medium", icon: "◐", action: "review before filing" },
  low: { label: "Low", icon: "○", action: "excluded — resolve evidence" },
};

export function confidenceMeta(c: Confidence) {
  return CONF_META[c];
}

/** Confidence chip: dot/icon + word, with an accessible label. */
export function ConfidenceBadge({ c, withTip = false }: { c: Confidence; withTip?: boolean }) {
  const m = CONF_META[c];
  const chip = (
    <span className={`tag ${c}`} role="img" aria-label={`${m.label} confidence — ${m.action}`}>
      <span className="mk" aria-hidden />
      <span aria-hidden>{m.icon}</span>
      {m.label}
    </span>
  );
  if (!withTip) return chip;
  return <Tip label={`${m.label} confidence → ${m.action}`} mono={false}>{chip}</Tip>;
}

/** In-headline / needs-review status, colour + glyph + word. */
export function HeadlineBadge({ inHeadline }: { inHeadline: boolean }) {
  return inHeadline ? (
    <span className="tag high" role="img" aria-label="In headline">
      <span aria-hidden>✓</span> In headline
    </span>
  ) : (
    <span className="tag medium" role="img" aria-label="Not in headline — needs review">
      <span aria-hidden>◷</span> Review
    </span>
  );
}

/** Render a legal citation as a live link when parseable, else plain mono text. */
export function Citation({ raw }: { raw: string }) {
  const c = parseCitation(raw);
  if (!c.href) return <span className="citetext">{c.text}</span>;
  return (
    <a className="citelink" href={c.href} target="_blank" rel="noopener noreferrer">
      {c.text}
      <span className="citesrc" aria-hidden>
        {c.source === "eCFR" ? "eCFR ↗" : "LII ↗"}
      </span>
    </a>
  );
}
