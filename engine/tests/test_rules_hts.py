"""HTS rules: normalization, 8-digit substitution standard, and the 'other'-basket exception (A-01/02)."""

from drawback.data.hts_reference import DEFAULT_REFERENCE as REF
from drawback.models import MatchBasis
from drawback.rules.hts import hts8, normalize_hts, substitution_match


def test_normalize_and_hts8():
    assert normalize_hts("8501.31.40.00") == "8501314000"
    assert normalize_hts("8501314000") == "8501314000"
    assert hts8("8501.31.40.00") == "85013140"


def test_same_8digit_substitutes():
    ok, basis, _ = substitution_match("8501314000", "8501319900", REF)  # same 8-digit 85013140? no
    # different 10-digit, same 8-digit 85013140 vs 85013199 -> different 8-digit, should fail
    assert ok is False
    ok, basis, _ = substitution_match("8501314000", "8501314055", REF)  # same 8-digit
    assert ok is True
    assert basis is MatchBasis.SUBSTITUTION_8_DIGIT


def test_different_8digit_no_substitution():
    ok, _basis, reason = substitution_match("8501314000", "8504409500", REF)
    assert ok is False
    assert "different 8-digit" in reason


def test_other_basket_drops_to_10_digit():
    # 73269086 begins with 'other'. 7326908635 -> 10-digit description NOT 'other' -> substitutes.
    ok, basis, _ = substitution_match("7326908635", "7326908635", REF)
    assert ok is True
    assert basis is MatchBasis.SUBSTITUTION_10_DIGIT


def test_other_basket_blocked_when_10digit_also_other():
    # 7326908688 -> 10-digit also 'other' -> no substitution at all (A-02).
    ok, _basis, reason = substitution_match("7326908688", "7326908688", REF)
    assert ok is False
    assert "other" in reason.lower()


def test_other_basket_different_10digit_no_match():
    ok, _basis, _ = substitution_match("7326908635", "7326908688", REF)
    assert ok is False
