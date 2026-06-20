#!/usr/bin/env python3
"""End-to-end demo on the real-format ingested dataset (COMPLIANCE.md Phase 2; `make demo`).

    PYTHONPATH=engine python scripts/demo.py

Runs the full chain a broker pilot would: ingest NetSuite commercial + CBP 7501/ACE + AES/EEI customs
data -> instant estimate -> the structurally-defensible (VERIFIED-only) headline + reconciliation report
-> a CATAIR claim file, finalized only after a (demo) licensed-filer sign-off. All synthetic/simulated;
nothing is transmitted to CBP.
"""

from __future__ import annotations

from pathlib import Path

from drawback.config import tariff_eligibility as cfg
from drawback.defensibility import harden
from drawback.estimate import build_estimate
from drawback.filing.catair import build_claims, mock_submit
from drawback.filing.signoff import FilerAttestation, FilerRole, record
from drawback.ingest import ingest_dataset

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def _h(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def main() -> None:
    _h("1. INGEST  (NetSuite commercial spine  ×  CBP 7501/ACE + AES/EEI customs overlay)")
    ds = ingest_dataset(SAMPLES / "demo_netsuite", SAMPLES / "demo_customs")
    dq = ds.data_quality
    print(f"   imports={dq.imports_parsed} (dropped {dq.imports_dropped})  "
          f"exports={dq.exports_parsed} (dropped {dq.exports_dropped})  "
          f"data-quality issues={len(dq.issues)}")

    _h("2. ESTIMATE")
    est = build_estimate(ds)
    print(f"   best estimate (point) = ${est.headline_point:,.2f}   conservative floor = ${est.headline_low:,.2f}")
    print(f"   potential (needs review) = ${est.potential_total:,.2f}   eligible duty pool = ${est.eligible_duty_pool:,.2f}")
    print(f"   matched pairs: {len(est.matched_pairs)}  ({len(est.headline_pairs())} in headline)")

    _h("3. DEFENSIBILITY  (structurally [VERIFIED]-only headline + reconciliation invariant)")
    rep = harden(est, strict=True).report()  # strict: raises if any cap/invariant is violated
    print(f"   DEFENSIBLE headline (audit-ready) = ${rep['defensible_headline']:,.2f}")
    print(f"   best estimate = ${rep['best_estimate']:,.2f}   needs review = ${rep['needs_review_total']:,.2f}")
    r = rep["reconciliation"]
    print(f"   reconciliation: {'OK' if r['ok'] else 'VIOLATION'} — "
          f"claimed ${r['total_claimed']:,.2f} ≤ duty paid ${r['duty_paid_on_claimed']:,.2f}")
    print(f"   rules fired by tier: {rep['tier_summary']}  "
          f"(only VERIFIED rules contribute to the defensible headline)")

    _h("4. CLAIM  (CATAIR file — finalized only after a licensed-filer sign-off)")
    charges_by_key = {(im.entry_number, im.line_number): im.charges for im in ds.imports}
    claims = build_claims(est, import_charges_by_key=charges_by_key)
    signoff = record(FilerAttestation(
        filer_name="Demo Broker, LCB", role=FilerRole.LICENSED_CUSTOMS_BROKER,
        attested_on=cfg.AS_OF.isoformat(), license_number="CHB-DEMO-0001", accepted_defensible=True,
        accepted_review_understood=True))
    manifest = mock_submit(claims, ROOT / "filing_out")
    manifest["signoff"] = signoff
    for c in manifest["claims"]:
        print(f"   claim {c['claim_number']} (provision {c['provision']}): "
              f"${c['grand_total_claimed']:,.2f}  {'✓ valid' if c['valid'] else c['issues']}")
    print(f"   signed off by: {signoff['filer_name']} ({signoff['role']}, {signoff['license_number']})")
    print(f"   files written to: {ROOT / 'filing_out'}   (SIMULATED — not transmitted to CBP)")

    _h("DONE — ingest → estimate → defensibility → signed claim, end to end.")


if __name__ == "__main__":
    main()
