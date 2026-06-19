"""Tariff-eligibility config (A-12/A-13) — the date-sensitive charge table."""

from drawback.config import tariff_eligibility as cfg
from drawback.models import ChargeType


def test_eligible_charges():
    for c in (ChargeType.BASE_DUTY, ChargeType.SECTION_301, ChargeType.MPF, ChargeType.HMF, ChargeType.EXCISE):
        assert cfg.is_eligible(c) is True, c


def test_ineligible_charges():
    for c in (ChargeType.SECTION_232, ChargeType.IEEPA, ChargeType.SECTION_122, ChargeType.AD_CVD):
        assert cfg.is_eligible(c) is False, c


def test_ieepa_routed_to_cape():
    assert ChargeType.IEEPA in cfg.CAPE_TRACK_CHARGES


def test_authority_present_for_every_charge():
    for c in ChargeType:
        assert cfg.authority(c)  # non-empty string
        assert cfg.note(c)


def test_config_summary_stamped():
    s = cfg.config_summary()
    assert s["as_of"] == "2026-06-19"
    assert "section_232" in s["ineligible"]
    assert "section_301" in s["eligible"]
