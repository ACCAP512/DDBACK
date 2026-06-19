"""Local HTSUS reference fixture (no paid API — PRD §6 seam).

Provides, per code: the 8-digit description, the "begins-with-'other'" flag (drives the A-02 basket
exception), the MFN base duty rate, and the Section 301 rate (0 if not 301-listed). MPF/HMF are flat
ad-valorem rates. In production this would be a licensed/maintained HTSUS dataset; here it is a curated
fixture covering the electronics/industrial-hardware persona (DECISIONS D-010) plus deliberate
"other"-basket cases to exercise the 10-digit fallback. Rates are realistic but illustrative.

⚠️  SEAM: swap this object for a real HTSUS reference and the rules/matcher are unchanged — they depend
    only on the duck-typed interface used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from drawback.models import ZERO
from drawback.rules.hts import hts8 as _hts8
from drawback.rules.hts import normalize_hts

MPF_RATE = Decimal("0.003464")   # 0.3464% ad valorem (per-unit-averaged approximation of the capped fee)
HMF_RATE = Decimal("0.00125")    # 0.125% ad valorem


@dataclass(frozen=True)
class HtsRecord:
    hts8: str
    description: str
    begins_with_other: bool
    base_rate: Decimal
    section_301_rate: Decimal
    unit: str = "No."


# Curated electronics / industrial-hardware codes. ``section_301_rate`` > 0 marks 301-listed lines.
_RECORDS: dict[str, HtsRecord] = {
    "85013140": HtsRecord("85013140", "Electric DC motors, of an output not exceeding 750 W", False, Decimal("0.028"), Decimal("0.25")),
    "85044095": HtsRecord("85044095", "Static converters (power supplies), other", False, Decimal("0.015"), Decimal("0.25")),
    "85365090": HtsRecord("85365090", "Switches for a voltage not exceeding 1,000 V, other", False, Decimal("0.027"), Decimal("0.25")),
    "85414900": HtsRecord("85414900", "Photosensitive semiconductor devices, other", False, ZERO, Decimal("0.25")),
    "85423100": HtsRecord("85423100", "Electronic integrated circuits: processors and controllers", False, ZERO, Decimal("0.25")),
    "84713001": HtsRecord("84713001", "Portable automatic data processing machines (laptops)", False, ZERO, Decimal("0.20")),
    "85176200": HtsRecord("85176200", "Machines for reception/conversion of voice, images or data (networking)", False, ZERO, Decimal("0.25")),
    "85444290": HtsRecord("85444290", "Insulated electric conductors fitted with connectors, other", False, Decimal("0.026"), Decimal("0.25")),
    "90138090": HtsRecord("90138090", "Liquid crystal devices, other optical appliances", False, Decimal("0.045"), Decimal("0.075")),
    "84733011": HtsRecord("84733011", "Parts and accessories of ADP machines, printed circuit assemblies", False, ZERO, Decimal("0.25")),
    "85285900": HtsRecord("85285900", "Monitors, other (not incorporating TV reception apparatus)", False, Decimal("0.05"), Decimal("0.25")),
    "85287200": HtsRecord("85287200", "Reception apparatus for television, color", False, ZERO, Decimal("0.25")),
    "85044085": HtsRecord("85044085", "Static converters: speed drive controllers for motors", False, ZERO, Decimal("0.25")),
    "85322500": HtsRecord("85322500", "Fixed capacitors, dielectric of paper or plastics", False, ZERO, Decimal("0.25")),
    "85332100": HtsRecord("85332100", "Fixed resistors, for a power handling capacity <= 20 W", False, ZERO, Decimal("0.25")),
    "85340000": HtsRecord("85340000", "Printed circuits", False, ZERO, Decimal("0.25")),
    "85389000": HtsRecord("85389000", "Parts for switching/protecting electrical circuits, other", False, Decimal("0.035"), Decimal("0.25")),
    "84679900": HtsRecord("84679900", "Parts of tools for working in the hand, other", False, ZERO, Decimal("0.25")),
    "84819000": HtsRecord("84819000", "Parts of taps, cocks, valves and similar appliances", False, Decimal("0.01"), Decimal("0.25")),
    "84099100": HtsRecord("84099100", "Parts for spark-ignition internal combustion engines", False, Decimal("0.025"), Decimal("0.25")),
    "90328900": HtsRecord("90328900", "Automatic regulating/controlling instruments, other", False, Decimal("0.017"), Decimal("0.25")),
    "90308900": HtsRecord("90308900", "Instruments for measuring electrical quantities, other", False, Decimal("0.016"), Decimal("0.25")),
    "76169951": HtsRecord("76169951", "Articles of aluminum, other", False, Decimal("0.025"), Decimal("0.075")),
    "94054000": HtsRecord("94054000", "Other electric lamps and lighting fittings", False, Decimal("0.035"), Decimal("0.25")),
    "39269097": HtsRecord("39269097", "Articles of plastics, other (face masks/components)", False, Decimal("0.05"), Decimal("0.075")),
    "85044040": HtsRecord("85044040", "Static converters: rectifiers and rectifying apparatus", False, Decimal("0.015"), Decimal("0.25")),
    "85176900": HtsRecord("85176900", "Other apparatus for transmission/reception of voice/data", False, ZERO, Decimal("0.25")),
    "85258900": HtsRecord("85258900", "Television cameras, digital cameras, other", False, Decimal("0.022"), Decimal("0.25")),
    "85299000": HtsRecord("85299000", "Parts for transmission/reception apparatus, other", False, Decimal("0.024"), Decimal("0.25")),
    "85369040": HtsRecord("85369040", "Terminals, electrical connectors", False, ZERO, Decimal("0.25")),
    "85371000": HtsRecord("85371000", "Boards/panels for electric control, <= 1,000 V", False, Decimal("0.027"), Decimal("0.25")),
    "85044070": HtsRecord("85044070", "Static converters: power supplies for ADP machines", False, ZERO, Decimal("0.25")),
    "84715001": HtsRecord("84715001", "Processing units (servers), other", False, ZERO, Decimal("0.20")),
    "84718000": HtsRecord("84718000", "Other units of automatic data processing machines", False, ZERO, Decimal("0.25")),
    "84829900": HtsRecord("84829900", "Parts of ball or roller bearings", False, Decimal("0.029"), Decimal("0.25")),
    "84833000": HtsRecord("84833000", "Bearing housings; plain shaft bearings", False, Decimal("0.045"), Decimal("0.25")),
    "85051100": HtsRecord("85051100", "Permanent magnets, of metal", False, Decimal("0.021"), Decimal("0.25")),
    "85076000": HtsRecord("85076000", "Lithium-ion accumulators (batteries)", False, Decimal("0.034"), Decimal("0.25")),
    "85389030": HtsRecord("85389030", "Printed circuit assemblies for switchgear", False, ZERO, Decimal("0.25")),
    "90251180": HtsRecord("90251180", "Thermometers, not combined with other instruments", False, ZERO, Decimal("0.25")),
    "90261000": HtsRecord("90261000", "Instruments for measuring flow/level of liquids", False, Decimal("0.016"), Decimal("0.25")),
    "90318000": HtsRecord("90318000", "Measuring/checking instruments, other", False, Decimal("0.013"), Decimal("0.25")),
    "73079900": HtsRecord("73079900", "Tube or pipe fittings of iron or steel, other", False, Decimal("0.043"), Decimal("0.25")),
    "76042900": HtsRecord("76042900", "Aluminum bars, rods and profiles, other", False, Decimal("0.05"), Decimal("0.075")),
    "94032000": HtsRecord("94032000", "Other metal furniture", False, ZERO, Decimal("0.25")),
    "39199000": HtsRecord("39199000", "Self-adhesive plates/film of plastics, other", False, Decimal("0.058"), Decimal("0.075")),
    "85318000": HtsRecord("85318000", "Electric sound or visual signaling apparatus, other", False, Decimal("0.013"), Decimal("0.25")),
    # ── "other"-basket subheadings: 8-digit description begins with "Other" (A-02) ──
    "73269086": HtsRecord("73269086", "Other articles of iron or steel, other", True, Decimal("0.029"), Decimal("0.25")),
    "39269099": HtsRecord("39269099", "Other articles of plastics, other", True, Decimal("0.053"), Decimal("0.075")),
}

# 10-digit statistical-suffix "begins-with-'other'" flags, for the A-02 basket fallback.
#   False -> the 10-digit description does NOT begin with "other" -> 10-digit substitution permitted.
#   True  -> it also begins with "other" -> no substitution at all.
_TEN_DIGIT_OTHER: dict[str, bool] = {
    "7326908635": False,  # "...containers..." — substitutable at 10-digit
    "7326908688": True,   # "Other" — not substitutable
    "3926909990": True,   # "Other" — not substitutable
    "3926909910": False,  # "Laboratory ware" — substitutable at 10-digit
}


class HtsReference:
    """Duck-typed interface consumed by ``rules.hts`` and ``rules.computation``."""

    def is_known(self, hts8_code: str) -> bool:
        return _hts8(hts8_code) in _RECORDS

    def record(self, hts8_code: str) -> HtsRecord | None:
        return _RECORDS.get(_hts8(hts8_code))

    def description(self, hts8_code: str) -> str:
        rec = self.record(hts8_code)
        return rec.description if rec else f"(unknown HTS {_hts8(hts8_code)})"

    def begins_with_other(self, hts8_code: str) -> bool:
        rec = self.record(hts8_code)
        return rec.begins_with_other if rec else False

    def begins_with_other_10(self, hts10_code: str) -> bool:
        h10 = normalize_hts(hts10_code)
        if h10 in _TEN_DIGIT_OTHER:
            return _TEN_DIGIT_OTHER[h10]
        # Unknown 10-digit under an "other" 8-digit: conservative -> assume it begins with "other"
        # (no substitution), so we never over-claim a basket we cannot confirm.
        return self.begins_with_other(h10[:8])

    def base_duty_rate(self, hts8_code: str) -> Decimal:
        rec = self.record(hts8_code)
        return rec.base_rate if rec else ZERO

    def section_301_rate(self, hts8_code: str) -> Decimal:
        rec = self.record(hts8_code)
        return rec.section_301_rate if rec else ZERO

    def mpf_rate(self) -> Decimal:
        return MPF_RATE

    def hmf_rate(self) -> Decimal:
        return HMF_RATE

    def known_codes(self) -> list[str]:
        return list(_RECORDS.keys())


DEFAULT_REFERENCE = HtsReference()
