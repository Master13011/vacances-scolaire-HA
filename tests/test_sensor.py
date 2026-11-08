"""Tests of the sensors and of the base entity (without a running Home Assistant)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant

from custom_components.vacances_scolaires.const import ATTRIBUTION, DOMAIN
from custom_components.vacances_scolaires.entity import get_entry_target
from custom_components.vacances_scolaires.sensor import (
    VacancesScolairesAujourdHuiSensor,
    VacancesScolairesDemainSensor,
    VacancesScolairesSensor,
)

from .common import make_entry, make_zone_entry

DATA = {
    "state": "Zone C - Holidays",
    "start_date": "08 novembre 2026 à 00:00:00 UTC",
    "end_date": "14 novembre 2026 à 22:00:00 UTC",
    "description": "Vacances de la Toussaint",
    "location": "Paris",
    "zone": "Zone C",
    "annee_scolaire": "2026-2027",
    "on_vacation": True,
}


def _coordinator(entry, data) -> MagicMock:
    coordinator = MagicMock()
    coordinator.config_entry = entry
    coordinator.data = data
    return coordinator


# --- get_entry_target --------------------------------------------------------


def test_entry_target_of_a_location_entry():
    assert get_entry_target(make_entry()) == ("location", "Paris")


def test_entry_target_of_a_zone_entry():
    assert get_entry_target(make_zone_entry("Zone B")) == ("zone", "Zone B")


def test_entry_target_defaults_to_location_when_type_is_missing():
    entry = MagicMock()
    entry.data = {"location": "Lyon"}
    assert get_entry_target(entry) == ("location", "Lyon")


def test_entry_target_is_unknown_when_the_name_is_missing():
    entry = MagicMock()
    entry.data = {"config_type": "zone"}
    assert get_entry_target(entry) == ("zone", "Unknown")


# --- identity (historical unique ids and names must not change) --------------


def test_location_sensor_unique_ids_and_names():
    coordinator = _coordinator(make_entry(), DATA)

    main = VacancesScolairesSensor(coordinator)
    today = VacancesScolairesAujourdHuiSensor(coordinator)
    tomorrow = VacancesScolairesDemainSensor(coordinator)

    assert main.unique_id == "vacances_scolaires_location_Paris"
    assert today.unique_id == "vacances_scolaires_location_Paris_today"
    assert tomorrow.unique_id == "vacances_scolaires_location_Paris_tomorrow"
    assert main.name == "Paris"
    assert today.name == "Aujourd'hui Paris"
    assert tomorrow.name == "Demain Paris"


def test_zone_sensor_unique_ids_and_names():
    coordinator = _coordinator(make_zone_entry("Zone C"), DATA)

    assert VacancesScolairesSensor(coordinator).unique_id == (
        "vacances_scolaires_zone_Zone C"
    )
    assert VacancesScolairesDemainSensor(coordinator).unique_id == (
        "vacances_scolaires_zone_Zone C_tomorrow"
    )
    assert VacancesScolairesAujourdHuiSensor(coordinator).name == "Aujourd'hui Zone C"


def test_sensors_share_the_device_and_attribution():
    entry = make_entry()
    coordinator = _coordinator(entry, DATA)

    for sensor in (
        VacancesScolairesSensor(coordinator),
        VacancesScolairesAujourdHuiSensor(coordinator),
        VacancesScolairesDemainSensor(coordinator),
    ):
        assert (DOMAIN, entry.entry_id) in sensor.device_info["identifiers"]
        assert sensor.device_info["name"] == "Vacances Scolaires"
        assert sensor.has_entity_name is True
        assert sensor.attribution == ATTRIBUTION


# --- main sensor -------------------------------------------------------------


def test_main_sensor_state_and_attributes():
    sensor = VacancesScolairesSensor(_coordinator(make_entry(), DATA))

    assert sensor.native_value == "Zone C - Holidays"
    assert sensor.extra_state_attributes == {
        "start_date": "08 novembre 2026 à 00:00:00 UTC",
        "end_date": "14 novembre 2026 à 22:00:00 UTC",
        "description": "Vacances de la Toussaint",
        "location": "Paris",
        "zone": "Zone C",
        "année_scolaire": "2026-2027",
        "en_vacances": True,
    }


@pytest.mark.parametrize("data", [None, {}])
def test_sensors_without_data_are_empty(data):
    coordinator = _coordinator(make_entry(), data)

    for sensor in (
        VacancesScolairesSensor(coordinator),
        VacancesScolairesAujourdHuiSensor(coordinator),
        VacancesScolairesDemainSensor(coordinator),
    ):
        assert sensor.native_value is None
        assert sensor.extra_state_attributes == {}


# --- today / tomorrow sensors ------------------------------------------------


def test_today_and_tomorrow_during_the_holidays():
    coordinator = _coordinator(make_entry(), DATA)

    with freeze_time("2026-11-10 12:00:00"):
        assert VacancesScolairesAujourdHuiSensor(coordinator).native_value == (
            "En vacances"
        )
        assert VacancesScolairesDemainSensor(coordinator).native_value == (
            "En vacances"
        )


def test_tomorrow_is_after_the_end_of_the_holidays():
    """The holidays end on the 14th at 22:00: the 15th is a school day."""
    coordinator = _coordinator(make_entry(), DATA)

    with freeze_time("2026-11-14 12:00:00"):
        assert VacancesScolairesAujourdHuiSensor(coordinator).native_value == (
            "En vacances"
        )
        assert VacancesScolairesDemainSensor(coordinator).native_value == (
            "Pas en vacances"
        )


def test_tomorrow_is_the_first_day_of_the_holidays():
    coordinator = _coordinator(make_entry(), DATA)

    with freeze_time("2026-11-07 23:00:00"):
        assert VacancesScolairesAujourdHuiSensor(coordinator).native_value == (
            "Pas en vacances"
        )
        assert VacancesScolairesDemainSensor(coordinator).native_value == (
            "En vacances"
        )


def test_today_before_and_after_the_holidays():
    coordinator = _coordinator(make_entry(), DATA)
    sensor = VacancesScolairesAujourdHuiSensor(coordinator)

    with freeze_time("2026-10-01 12:00:00"):
        assert sensor.native_value == "Pas en vacances"
    with freeze_time("2026-12-01 12:00:00"):
        assert sensor.native_value == "Pas en vacances"


def test_day_sensors_follow_the_coordinator_data():
    coordinator = _coordinator(make_entry(), DATA)
    sensor = VacancesScolairesAujourdHuiSensor(coordinator)

    with freeze_time("2026-11-10 12:00:00"):
        assert sensor.native_value == "En vacances"
        coordinator.data = {
            **DATA,
            "start_date": "20 décembre 2026 à 00:00:00 UTC",
            "end_date": "03 janvier 2027 à 00:00:00 UTC",
        }
        assert sensor.native_value == "Pas en vacances"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("n'importe quoi", "14 novembre 2026 à 22:00:00 UTC"),
        ("08 novembre 2026 à 00:00:00 UTC", ""),
        (None, None),
        (12345, 67890),
    ],
)
def test_day_sensors_are_unknown_when_dates_are_unusable(start, end):
    coordinator = _coordinator(
        make_entry(), {**DATA, "start_date": start, "end_date": end}
    )

    assert VacancesScolairesAujourdHuiSensor(coordinator).native_value is None
    assert VacancesScolairesDemainSensor(coordinator).native_value is None


# --- midnight refresh ----------------------------------------------------------


async def test_day_sensors_register_a_refresh_just_after_midnight(
    hass: HomeAssistant,
) -> None:
    sensor = VacancesScolairesAujourdHuiSensor(_coordinator(make_entry(), DATA))
    sensor.hass = hass

    with patch(
        "custom_components.vacances_scolaires.sensor.async_track_time_change"
    ) as track:
        await sensor.async_added_to_hass()

    track.assert_called_once()
    assert track.call_args.args[0] is hass
    assert track.call_args.kwargs == {"hour": 0, "minute": 0, "second": 5}
    assert track.call_args.args[1] == sensor._handle_midnight_update


async def test_midnight_refresh_rewrites_the_state() -> None:
    sensor = VacancesScolairesDemainSensor(_coordinator(make_entry(), DATA))

    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_midnight_update(MagicMock())

    write.assert_called_once()
