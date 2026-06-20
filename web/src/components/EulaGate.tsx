// One-time entry gate (COMPLIANCE §1.5 / P4): the field-of-use restriction that
// EFFECTS the operate-vs-license burden-shift. On first visit, a focus-trapped
// Radix Dialog presents the decision-support disclaimer + asks the user to
// attest which lawful category they fall in:
//   (a) a licensed customs broker / attorney,
//   (b) an importer/exporter evaluating for self-filing on its own account, or
//   (c) someone evaluating the software.
// The acknowledgement (category + timestamp) is persisted in
// localStorage("drawback-eula-ack"); re-visits are NOT blocked once acknowledged.

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useStored } from "../storage";
import { DISCLAIMER_TEXT } from "./Disclaimer";

type Audience = "broker_attorney" | "self_filer" | "evaluating";

interface Ack {
  acknowledged: boolean;
  audience: Audience;
  at: string; // ISO timestamp
}

const EMPTY_ACK: Ack = { acknowledged: false, audience: "evaluating", at: "" };

const OPTIONS: { value: Audience; label: string; hint: string }[] = [
  {
    value: "broker_attorney",
    label: "A licensed U.S. customs broker or customs attorney",
    hint: "You operate the tool under your own license and judgment.",
  },
  {
    value: "self_filer",
    label: "An importer/exporter evaluating self-filing on its own account",
    hint: "Exempt under 19 CFR 111.2(a)(2)(i) — you act for no one but yourself.",
  },
  {
    value: "evaluating",
    label: "Evaluating the software",
    hint: "Reviewing the product; not processing a real claim or real data.",
  },
];

/**
 * Mounts at the app root. Renders nothing once acknowledged. While open it
 * blocks interaction with the page (modal), but it only ever shows on the first
 * visit per browser; the choice is remembered.
 */
export default function EulaGate() {
  const [ack, setAck] = useStored<Ack>("drawback-eula-ack", EMPTY_ACK);
  // On a fresh visit default the selection to the most common lawful operator
  // (a broker/attorney); only inherit a prior pick if one was actually made.
  const [choice, setChoice] = useState<Audience>(
    ack.acknowledged ? ack.audience : "broker_attorney",
  );

  if (ack.acknowledged) return null;

  function accept() {
    setAck({ acknowledged: true, audience: choice, at: new Date().toISOString() });
  }

  return (
    // Controlled + non-dismissable: ignore overlay-click / ESC close attempts so
    // the field-of-use attestation can't be skipped. (No Close button rendered.)
    <Dialog.Root open onOpenChange={() => {}}>
      <Dialog.Portal>
        <Dialog.Overlay className="scrim eula-scrim" />
        <Dialog.Content
          className="eula"
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <div className="eula-head">
            <span className="eula-mark" aria-hidden>
              <ShieldIcon />
            </span>
            <div>
              <Dialog.Title className="eula-title">
                Before you continue
              </Dialog.Title>
              <Dialog.Description className="eula-sub">
                This tool is licensed for a specific, lawful field of use. Please
                read and confirm.
              </Dialog.Description>
            </div>
          </div>

          <p className="eula-disc">{DISCLAIMER_TEXT}</p>

          <div
            className="eula-choices"
            role="radiogroup"
            aria-label="I am using this software as"
          >
            <div className="eula-choices-lab">I am using this software as…</div>
            {OPTIONS.map((o) => {
              const active = choice === o.value;
              return (
                <button
                  type="button"
                  key={o.value}
                  role="radio"
                  aria-checked={active}
                  className={`eula-choice ${active ? "active" : ""}`}
                  onClick={() => setChoice(o.value)}
                >
                  <span className="radio" aria-hidden>
                    <span className="dot" />
                  </span>
                  <span className="ct">
                    <span className="lab">{o.label}</span>
                    <span className="hint">{o.hint}</span>
                  </span>
                </button>
              );
            })}
          </div>

          <p className="eula-fine">
            The software does not transact customs business and does not file with
            CBP; a licensed filer must independently review and file. Pricing is a
            flat software fee — never a percentage of any recovery.
          </p>

          <div className="eula-actions">
            <button className="btn primary" type="button" onClick={accept} autoFocus>
              I understand &amp; agree
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ShieldIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
