"""Layer 3 (stubbed): build a CATAIR-shaped drawback claim from the headline pairs, validate it, and
'mock-submit' it to a file. NOTHING is transmitted to CBP (DECISIONS D-009; PRD §4.5/§7).

The record structure follows the ACE ABI CATAIR Drawback (TFTEA) chapter (RESEARCH Q17): a 10 header,
40/41/42/43 import-designation records (with ITINs + revenue by accounting-class code), 70/71/72
export records linking back to import ITINs, and 89/90 totals. A real filing layer would emit the
exact 80-char fixed-width records and transmit via ABI under a CBP entry filer code — that swap is a
contained change behind this interface.

⚠️  SIMULATED — NOT CONNECTED TO CBP. A licensed broker/filer must certify and transmit (19 CFR 190.6).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from drawback.models import ZERO, ChargeType, DrawbackProvision, Estimate, MatchedPair

# Accounting-class codes (CATAIR Appendix D, drawback subset — RESEARCH Q17).
_ACCT = {
    ChargeType.BASE_DUTY: "364", ChargeType.SECTION_301: "364",   # 364 Drawback Duty
    ChargeType.MPF: "399",                                         # 399 Drawback MPF
    ChargeType.HMF: "398",                                         # 398 Drawback HMF
    ChargeType.EXCISE: "365",                                      # 365 Drawback Tax(es)
}
SIMULATED_BANNER = "SIMULATED — NOT TRANSMITTED TO CBP. For licensed-filer review only (19 CFR 190.6)."


def _q(d: Decimal) -> float:
    return float(round(d, 2))


@dataclass
class ImportRecord:   # 40/41/42/43
    itin: int
    entry_filer_code: str
    entry_number: str
    cbp_line: int
    hts10: str
    quantity: int
    entered_value_per_unit: float
    accounting_method_code: str
    revenue_claimed: dict          # acct_code -> amount (99% of duties/taxes/fees)


@dataclass
class ExportRecord:   # 70/71/72
    action: str
    hts10: str
    quantity: int
    export_date: str
    destination_country: str
    bol_indicator: bool
    bol_carrier_scac: str
    unique_identifier: str
    linked_itins: list[int]


@dataclass
class CatairClaim:    # 10 header + records + 89/90 totals
    filing_action: str
    application_identifier: str
    entry_filer_code: str
    claim_number: str
    filing_port: str
    drawback_provision_code: str
    drawback_provision_label: str
    claimant_id: str
    accelerated_payment: bool
    electronic_signature: str
    imports: list[ImportRecord] = field(default_factory=list)
    exports: list[ExportRecord] = field(default_factory=list)
    totals: dict = field(default_factory=dict)        # 89/90 by accounting class + grand totals
    simulated: bool = True
    banner: str = SIMULATED_BANNER


def _apportion(pair_recoveries: list[MatchedPair], import_charges: dict) -> dict:
    """Split a designated import's claimed recovery across accounting-class codes in proportion to its
    eligible charge mix (so 364 duty / 399 MPF / 398 HMF reconcile to the total claimed)."""
    total_recovery = sum((p.recovery for p in pair_recoveries), ZERO)
    eligible = {c: a for c, a in import_charges.items() if c in _ACCT and a > 0}
    eligible_total = sum(eligible.values(), ZERO)
    out: dict[str, Decimal] = {}
    if eligible_total <= 0:
        return {"364": _q(total_recovery)}
    allocated = ZERO
    items = list(eligible.items())
    for idx, (charge, amt) in enumerate(items):
        acct = _ACCT[charge]
        if idx == len(items) - 1:
            share = total_recovery - allocated   # last bucket absorbs rounding
        else:
            share = (total_recovery * amt / eligible_total).quantize(Decimal("0.01"))
            allocated += share
        out[acct] = out.get(acct, ZERO) + share
    return {k: _q(v) for k, v in out.items()}


def build_claims(
    estimate: Estimate,
    *,
    entry_filer_code: str = "ZZZ",
    filing_port: str = "1001",
    claimant_id: str = "47-3319008",
    accelerated_payment: bool = True,
    import_charges_by_key: dict | None = None,
) -> list[CatairClaim]:
    """One CATAIR claim per drawback provision present in the headline. ``import_charges_by_key`` maps
    (entry_number, line_no) -> the import's charge dict, for accounting-class apportionment."""
    import_charges_by_key = import_charges_by_key or {}
    by_provision: dict[DrawbackProvision, list[MatchedPair]] = {}
    for p in estimate.headline_pairs():
        by_provision.setdefault(p.provision, []).append(p)

    claims: list[CatairClaim] = []
    for seq, (prov, pairs) in enumerate(sorted(by_provision.items(), key=lambda kv: kv[0].value), start=1):
        itin_counter = 0
        imports: list[ImportRecord] = []
        exports: list[ExportRecord] = []
        # group pairs by designated import -> one import record + ITIN
        by_import: dict[tuple[str, int], list[MatchedPair]] = {}
        for p in pairs:
            by_import.setdefault((p.import_entry, p.import_line_no), []).append(p)

        itin_for_import: dict[tuple[str, int], int] = {}
        for key, ps in by_import.items():
            itin_counter += 1
            itin_for_import[key] = itin_counter
            charges = import_charges_by_key.get(key, {})
            imports.append(ImportRecord(
                itin=itin_counter, entry_filer_code=key[0][:3] if key[0] else entry_filer_code,
                entry_number=key[0], cbp_line=key[1], hts10=ps[0].hts8 + "00",
                quantity=sum(p.quantity for p in ps),
                entered_value_per_unit=float(ps[0].per_unit_designated_duty),
                accounting_method_code="00" if prov in (DrawbackProvision.J1_UNUSED_DIRECT,
                                                         DrawbackProvision.A_MFG_DIRECT) else "01",
                revenue_claimed=_apportion(ps, charges),
            ))
        for p in pairs:
            exports.append(ExportRecord(
                action="E", hts10=p.hts8 + "00", quantity=p.quantity,
                export_date=p.trace.export_date.isoformat(), destination_country="CA",
                bol_indicator=True, bol_carrier_scac="MAEU", unique_identifier=p.export_reference,
                linked_itins=[itin_for_import[(p.import_entry, p.import_line_no)]],
            ))

        grand = sum((p.recovery for p in pairs), ZERO)
        by_acct: dict[str, float] = {}
        for rec in imports:
            for acct, amt in rec.revenue_claimed.items():
                by_acct[acct] = round(by_acct.get(acct, 0.0) + amt, 2)
        claims.append(CatairClaim(
            filing_action="A", application_identifier="DE", entry_filer_code=entry_filer_code,
            claim_number=f"{entry_filer_code}-{seq:07d}", filing_port=filing_port,
            drawback_provision_code=prov.value, drawback_provision_label=prov.name,
            claimant_id=claimant_id, accelerated_payment=accelerated_payment,
            electronic_signature="X (claimant/broker certification gate — 19 CFR 190.6)",
            imports=imports, exports=exports,
            totals={"by_accounting_class": by_acct, "grand_total_claimed": _q(grand)},
        ))
    return claims


def validate_claim(claim: CatairClaim) -> list[str]:
    """Structural validation a real ABI submission would have to pass. Returns a list of issues."""
    issues: list[str] = []
    if not claim.imports:
        issues.append("no import-designation (40) records")
    if not claim.exports:
        issues.append("no export (70) records")
    itins = {imp.itin for imp in claim.imports}
    for ex in claim.exports:
        for link in ex.linked_itins:
            if link not in itins:
                issues.append(f"export {ex.unique_identifier} links to unknown ITIN {link}")
    # totals reconcile
    acct_sum = round(sum(claim.totals.get("by_accounting_class", {}).values()), 2)
    if abs(acct_sum - claim.totals.get("grand_total_claimed", 0.0)) > 0.05:
        issues.append(f"accounting-class total {acct_sum} != grand total {claim.totals.get('grand_total_claimed')}")
    if claim.accelerated_payment and not claim.electronic_signature:
        issues.append("accelerated payment requested without a certification signature")
    return issues


def serialize_claim_text(claim: CatairClaim) -> str:
    """A readable, record-typed rendering of the would-be ABI transmission (not the exact 80-char wire
    format — that is the production seam). Header lines mark it SIMULATED."""
    lines = [
        f"* {SIMULATED_BANNER}",
        f"* ACE ABI CATAIR Drawback (TFTEA) — application id {claim.application_identifier}",
        f"10|{claim.filing_action}|filer={claim.entry_filer_code}|claim={claim.claim_number}"
        f"|port={claim.filing_port}|provision={claim.drawback_provision_code}({claim.drawback_provision_label})"
        f"|claimant={claim.claimant_id}|AP={'Y' if claim.accelerated_payment else 'N'}|sig={claim.electronic_signature}",
    ]
    for imp in claim.imports:
        lines.append(f"40|ITIN={imp.itin}|{imp.entry_filer_code}|{imp.entry_number}|line={imp.cbp_line}"
                     f"|method={imp.accounting_method_code}")
        lines.append(f"41|HTS={imp.hts10}|qty={imp.quantity}")
        lines.append(f"42|qty={imp.quantity}|entered_value_per_unit={imp.entered_value_per_unit}")
        for acct, amt in imp.revenue_claimed.items():
            lines.append(f"43|acct_class={acct}|claim_amount={amt:.2f}")
    for ex in claim.exports:
        lines.append(f"70|{ex.action}|HTS={ex.hts10}|qty={ex.quantity}|export_date={ex.export_date}"
                     f"|dest={ex.destination_country}|BOL={'Y' if ex.bol_indicator else 'N'}|SCAC={ex.bol_carrier_scac}")
        lines.append(f"71|unique_id={ex.unique_identifier}")
        lines.append(f"72|linked_ITINs={','.join(map(str, ex.linked_itins))}")
    for acct, amt in claim.totals.get("by_accounting_class", {}).items():
        lines.append(f"89|acct_class={acct}|total={amt:.2f}")
    lines.append(f"90|grand_total_claimed={claim.totals.get('grand_total_claimed', 0.0):.2f}")
    return "\n".join(lines)


def mock_submit(claims: list[CatairClaim], out_dir: str | Path = "filing_out") -> dict:
    """Write the would-be transmission + a manifest to disk and validate. Returns the manifest.
    SIMULATED — writes files only; transmits nothing."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"simulated": True, "banner": SIMULATED_BANNER, "claims": []}
    for claim in claims:
        issues = validate_claim(claim)
        stem = claim.claim_number.replace("/", "-")
        (out / f"{stem}.catair.txt").write_text(serialize_claim_text(claim))
        (out / f"{stem}.json").write_text(json.dumps(asdict(claim), indent=2, default=str))
        manifest["claims"].append({
            "claim_number": claim.claim_number, "provision": claim.drawback_provision_code,
            "grand_total_claimed": claim.totals.get("grand_total_claimed", 0.0),
            "valid": not issues, "issues": issues,
            "files": [f"{stem}.catair.txt", f"{stem}.json"],
        })
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
