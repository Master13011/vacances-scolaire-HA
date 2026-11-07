"""Tests of the small helpers."""

from custom_components.vacances_scolaires.util import (
    normalize_text,
    sanitize_update_interval,
)


def test_normalize_text_strips_accents_and_case() -> None:
    assert normalize_text("Élèves") == "eleves"
    assert normalize_text("Nouvelle Calédonie") == "nouvelle caledonie"
    assert normalize_text("Zone A") == "zone a"


def test_normalize_text_handles_empty_values() -> None:
    assert normalize_text(None) == ""
    assert normalize_text("") == ""


def test_sanitize_update_interval_keeps_valid_values() -> None:
    assert sanitize_update_interval(1) == 1
    assert sanitize_update_interval(12) == 12
    assert sanitize_update_interval("24") == 24
    assert sanitize_update_interval(168) == 168


def test_sanitize_update_interval_clamps_out_of_range_values() -> None:
    # 0 or negative values would make the coordinator refresh in a tight loop
    assert sanitize_update_interval(0) == 1
    assert sanitize_update_interval(-5) == 1
    assert sanitize_update_interval(9999) == 168


def test_sanitize_update_interval_falls_back_on_garbage() -> None:
    assert sanitize_update_interval(None) == 12
    assert sanitize_update_interval("abc") == 12
