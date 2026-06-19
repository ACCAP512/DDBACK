#!/usr/bin/env python3
"""Generate the committed sample data + a reference estimate so a reviewer can load it instantly.

    PYTHONPATH=engine python scripts/make_samples.py

Writes (all clearly-labelled synthetic data, isolated from any real-data path — DECISIONS D-010):
    samples/imports.csv, samples/exports.csv         ACE/ITRAC-like seed data
    samples/sample_estimate.json                      reference Layer-1/2 output
    samples/sample_lifecycle.json                     simulated Layer-3 status
    samples/filing_out/                               simulated CATAIR claim files + manifest
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from drawback.config import tariff_eligibility as cfg
from drawback.data.generator import generate, write_csvs
from drawback.data.parser import parse_dataset
from drawback.estimate import build_estimate
from drawback.filing.catair import build_claims, mock_submit
from drawback.filing.lifecycle import simulate_lifecycle
from drawback.serialize import estimate_to_dict

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def main() -> None:
    SAMPLES.mkdir(exist_ok=True)
    ds = generate(seed=42, scale="demo")
    imp_path, exp_path = write_csvs(ds, SAMPLES)

    # Round-trip through the parser so the committed CSV is the source of truth.
    parsed = parse_dataset(imp_path, exp_path)
    est = build_estimate(parsed)
    (SAMPLES / "sample_estimate.json").write_text(json.dumps(estimate_to_dict(est), indent=2))

    charges_by_key = {(im.entry_number, im.line_number): im.charges for im in parsed.imports}
    claims = build_claims(est, import_charges_by_key=charges_by_key)
    mock_submit(claims, SAMPLES / "filing_out")

    lc = simulate_lifecycle(cfg.AS_OF, accelerated_payment=True,
                            estimated_amount=est.headline_point, today=cfg.AS_OF)
    (SAMPLES / "sample_lifecycle.json").write_text(json.dumps(lc, indent=2))

    print(f"imports={len(parsed.imports)} exports={len(parsed.exports)}")
    print(f"headline=${est.headline_point:,.2f}  low=${est.headline_low:,.2f}  potential=${est.potential_total:,.2f}")
    print(f"claims={len(claims)}  files -> {SAMPLES/'filing_out'}")
    print(f"wrote: {imp_path.name}, {exp_path.name}, sample_estimate.json, sample_lifecycle.json")


if __name__ == "__main__":
    main()
