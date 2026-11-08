"""Tests of the coordinator: date handling, timezones and error mapping."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.vacances_scolaires.api import (
    VacancesScolairesApiError,
    VacancesScolairesNoDataError,
)
from custom_components.vacances_scolaires.const import CONF_CONFIG_TYPE
from custom_components.vacances_scolaires.coordinator import (
    VacancesScolairesDataUpdateCoordinator,
    get_timezone,
    traduire_mois,
)

from .common import FETCH, make_entry, make_zone_entry

SESSION = "custom_components.vacances_scolaires.coordinator.async_get_clientsession"


def _record(start: str, end: str, **overrides) -> dict:
    """Return an API record with fixed dates."""
    record = {
        "start_date": start,
        "end_date": end,
        "description": "Vacances de la Toussaint",
        "location": "Paris",
        "zones": "Zone C",
        "annee_scolaire": "2026-2027",
        "population": "-",
    }
    record.update(overrides)
    return record


# 8 -> 15 November 2026
TOUSSAINT = _record("2026-11-08T00:00:00+00:00", "2026-11-15T00:00:00+00:00")


async def _refresh(hass: HomeAssistant, entry, records) -> dict:
    """Run one update of a coordinator built for ``entry``."""
    entry.add_to_hass(hass)
    coordinator = VacancesScolairesDataUpdateCoordinator(hass, entry)
    with patch(FETCH, return_value=records), patch(SESSION, return_value=MagicMock()):
        return await coordinator._async_update_data()


# --- traduire_mois -----------------------------------------------------------


@pytest.mark.parametrize(
    ("english", "french"),
    [
        ("January", "janvier"),
        ("February", "février"),
        ("March", "mars"),
        ("April", "avril"),
        ("May", "mai"),
        ("June", "juin"),
        ("July", "juillet"),
        ("August", "août"),
        ("September", "septembre"),
        ("October", "octobre"),
        ("November", "novembre"),
        ("December", "décembre"),
    ],
)
def test_traduire_mois_translates_every_month(english, french):
    assert traduire_mois(f"05 {english} 2026 à 22:00:00 UTC") == (
        f"05 {french} 2026 à 22:00:00 UTC"
    )


def test_traduire_mois_leaves_other_text_untouched():
    assert traduire_mois("déjà en français : 17 octobre") == (
        "déjà en français : 17 octobre"
    )
    assert traduire_mois("") == ""


# --- get_timezone ------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "timezone"),
    [
        ("Guadeloupe", "America/Guadeloupe"),
        ("Guyane", "America/Cayenne"),
        ("Martinique", "America/Martinique"),
        ("Mayotte", "Indian/Mayotte"),
        ("Nouvelle Calédonie", "Pacific/Noumea"),
        ("Polynésie française", "Pacific/Tahiti"),
        ("Réunion", "Indian/Reunion"),
        ("Saint Pierre et Miquelon", "America/Miquelon"),
        ("Wallis et Futuna", "Pacific/Wallis"),
    ],
)
def test_overseas_locations_have_their_own_timezone(location, timezone):
    assert get_timezone(location) == timezone
    ZoneInfo(timezone)  # the zone must exist in the tz database


@pytest.mark.parametrize("location", ["Paris", "Corse", "Zone A", "", "Inconnue"])
def test_other_locations_use_paris_time(location):
    assert get_timezone(location) == "Europe/Paris"


# --- state computation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("now", "on_vacation"),
    [
        ("2026-11-07 23:59:59", False),  # the day before the start
        ("2026-11-08 00:00:00", True),  # first day
        ("2026-11-12 15:30:00", True),
        ("2026-11-15 00:00:00", True),  # last day
        ("2026-11-15 23:59:59", True),  # the whole last day counts
        ("2026-11-16 00:00:00", False),  # the day after the end
    ],
)
async def test_on_vacation_boundaries(hass: HomeAssistant, now, on_vacation) -> None:
    with freeze_time(now):
        data = await _refresh(hass, make_entry(), [TOUSSAINT])

    assert data["on_vacation"] is on_vacation
    assert data["state"] == ("Zone C - Holidays" if on_vacation else "Zone C - Work")


async def test_state_uses_the_zone_of_the_record(hass: HomeAssistant) -> None:
    record = _record(
        "2026-11-08T00:00:00+00:00", "2026-11-15T00:00:00+00:00", zones="Corse"
    )
    with freeze_time("2026-11-10 12:00:00"):
        data = await _refresh(hass, make_entry(), [record])

    assert data["state"] == "Corse - Holidays"
    assert data["zone"] == "Corse"


async def test_dates_are_formatted_in_french(hass: HomeAssistant) -> None:
    with freeze_time("2026-11-10 12:00:00"):
        data = await _refresh(hass, make_entry(), [TOUSSAINT])

    assert data["start_date"] == "08 novembre 2026 à 00:00:00 UTC"
    assert data["end_date"] == "15 novembre 2026 à 00:00:00 UTC"


async def test_dates_keep_the_utc_time_sent_by_the_api(hass: HomeAssistant) -> None:
    """Academies start at 22:00 UTC the evening before (midnight in Paris)."""
    record = _record("2026-10-17T22:00:00+00:00", "2026-11-02T22:00:00+00:00")
    with freeze_time("2026-10-20 12:00:00"):
        data = await _refresh(hass, make_entry(), [record])

    assert data["start_date"] == "17 octobre 2026 à 22:00:00 UTC"
    assert data["end_date"] == "02 novembre 2026 à 22:00:00 UTC"


async def test_returned_data_contains_the_record_details(hass: HomeAssistant) -> None:
    with freeze_time("2026-11-10 12:00:00"):
        data = await _refresh(hass, make_entry(), [TOUSSAINT])

    assert data["description"] == "Vacances de la Toussaint"
    assert data["location"] == "Paris"
    assert data["annee_scolaire"] == "2026-2027"
    assert set(data) == {
        "state",
        "start_date",
        "end_date",
        "description",
        "location",
        "zone",
        "annee_scolaire",
        "on_vacation",
    }


async def test_missing_optional_fields_give_none(hass: HomeAssistant) -> None:
    record = {
        "start_date": "2026-11-08T00:00:00+00:00",
        "end_date": "2026-11-15T00:00:00+00:00",
        "description": "Vacances",
        "zones": "Zone C",
    }
    with freeze_time("2026-11-10 12:00:00"):
        data = await _refresh(hass, make_entry(), [record])

    assert data["location"] is None
    assert data["annee_scolaire"] is None


# --- errors ------------------------------------------------------------------


async def test_unknown_config_type_fails_the_update(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_CONFIG_TYPE: "bogus"})
    entry.add_to_hass(hass)
    coordinator = VacancesScolairesDataUpdateCoordinator(hass, entry)

    with patch(FETCH) as fetch, pytest.raises(UpdateFailed, match="Invalid configuration"):
        await coordinator._async_update_data()

    fetch.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [VacancesScolairesApiError("API is down"), VacancesScolairesNoDataError("API is down")],
)
async def test_api_errors_become_update_failed(hass: HomeAssistant, error) -> None:
    entry = make_zone_entry("Zone C")
    entry.add_to_hass(hass)
    coordinator = VacancesScolairesDataUpdateCoordinator(hass, entry)

    with (
        patch(FETCH, side_effect=error),
        patch(SESSION, return_value=MagicMock()),
        pytest.raises(UpdateFailed, match="API is down"),
    ):
        await coordinator._async_update_data()
