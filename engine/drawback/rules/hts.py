"""HTSUS classification rules: normalization, the 8-digit substitution standard, and the
"other"-basket 10-digit exception.

Citations: 19 U.S.C. 1313(b)(1), (j)(2), (j)(5); 19 CFR 190.2. RESEARCH Q2/Q16.
Assumptions: A-01 (8-digit standard), A-02 ("other"->10-digit), A-04 (applies to (b) and (j)(2)),
A-20 (compare the 8-digit prefix).

The HTS reference (descriptions / "begins-with-other" flags / duty rates) is injected so this module
stays pure logic — see ``drawback.data.hts_reference`` for the data and the duck-typed interface:
    ref.begins_with_other(hts8: str) -> bool
    ref.begins_with_other_10(hts10: str) -> bool
"""

from __future__ import annotations

from typing import Optional

from drawback.models import MatchBasis


def normalize_hts(code: str) -> str:
    """Strip formatting to a digits-only HTS string (e.g. '8501.31.40.00' -> '8501314000').

    Returns up to 10 digits. Shorter inputs are returned as-is (the parser flags those as a
    data-quality issue); longer inputs are truncated to 10 (statistical suffix is the last 2)."""
    digits = "".join(ch for ch in code if ch.isdigit())
    return digits[:10]


def hts8(code: str) -> str:
    """The 8-digit tariff-rate line — the substitution key (A-20). The 9-10 statistical suffix is
    ignored for substitution but retained elsewhere for reporting."""
    return normalize_hts(code)[:8]


def is_valid_hts10(code: str) -> bool:
    return len(normalize_hts(code)) == 10


def substitution_match(
    designated_hts10: str,
    substituted_hts10: str,
    ref,
) -> tuple[bool, Optional[MatchBasis], str]:
    """Decide whether ``substituted`` (the exported article) may be substituted for ``designated``
    (the imported article) under the current 8-digit standard and the "other"-basket exception.

    Returns (allowed, basis, reason).

    Rule (A-01/A-02/A-04):
      1. If the two share the same 8-digit subheading:
         - If that 8-digit subheading's article description begins with "other", the 8-digit basis is
           disqualified (1313(j)(5)(A)); substitution is allowed only if both share the same 10-digit
           statistical number AND that 10-digit description does not begin with "other" (1313(j)(5)(B)).
         - Otherwise the 8-digit match stands.
      2. Different 8-digit subheadings never substitute.
    """
    d8, s8 = hts8(designated_hts10), hts8(substituted_hts10)

    if d8 != s8:
        return False, None, f"different 8-digit subheading ({d8} vs {s8}) — 19 CFR 190.2 / 1313(j)(2)"

    if not ref.begins_with_other(d8):
        return True, MatchBasis.SUBSTITUTION_8_DIGIT, f"same 8-digit subheading {d8} (19 CFR 190.2)"

    # "Other"-basket exception (1313(j)(5)): drop to a 10-digit match.
    d10, s10 = normalize_hts(designated_hts10), normalize_hts(substituted_hts10)
    if d10 == s10 and not ref.begins_with_other_10(d10):
        return (
            True,
            MatchBasis.SUBSTITUTION_10_DIGIT,
            f"8-digit subheading {d8} begins with 'other'; matched at 10-digit {d10} "
            f"whose description does not begin with 'other' (1313(j)(5)(B))",
        )
    if d10 == s10:  # same 10-digit but it too begins with "other" -> no substitution
        return (
            False,
            None,
            f"8-digit and 10-digit descriptions both begin with 'other' — no substitution (1313(j)(5))",
        )
    return (
        False,
        None,
        f"8-digit subheading {d8} begins with 'other'; 10-digit numbers differ "
        f"({d10} vs {s10}) — no substitution (1313(j)(5)(A))",
    )


def is_direct_identification(designated_hts10: str, substituted_hts10: str) -> bool:
    """True when the exported article is classified identically (same 10-digit) to the designated
    import — a *necessary* (not sufficient) condition for a (j)(1) direct-ID claim. Sufficiency also
    needs lot/identification evidence (A-08), which the data layer supplies via an explicit link."""
    return normalize_hts(designated_hts10) == normalize_hts(substituted_hts10)
