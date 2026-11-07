"""Tests of the integration setup, coordinator and sensors."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.vacances_scolaires.api import (
    VacancesScolairesApiError,
    VacancesScolairesNoDataError,
)
from custom_components.vacances_scolaires.const import (
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.vacances_scolaires.coordinator import (
    VacancesScolairesDataUpdateCoordinator,
)
from custom_components.vacances_scolaires.sensor import convert_to_iso_format

from .common import FETCH, make_entry, make_record, make_zone_entry


async def _setup(hass: HomeAssistant, entry, records) -> None:
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=records):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


# --- setup / unload ----------------------------------------------------------


async def test_setup_and_unload(hass: HomeAssistant) -> None:
    entry = make_entry()
    await _setup(hass, entry, [make_record()])

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, VacancesScolairesDataUpdateCoordinator)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_api_is_unreachable(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch(FETCH, side_effect=VacancesScolairesApiError("boom")):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_retries_when_there_is_no_data(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch(FETCH, side_effect=VacancesScolairesNoDataError("nothing")):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_only_sensors_are_created_without_calendar(hass: HomeAssistant) -> None:
    entry = make_entry()
    await _setup(hass, entry, [make_record()])
    assert not hass.states.async_entity_ids("calendar")
    assert len(hass.states.async_entity_ids("sensor")) == 3


# --- request ---------------------------------------------------------------


async def test_location_entry_queries_the_location(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=[make_record()]) as fetch:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert fetch.await_args.args[1:] == ("location", "Paris")


async def test_zone_entry_queries_the_zone(hass: HomeAssistant) -> None:
    entry = make_zone_entry("Zone C")
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=[make_record()]) as fetch:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert fetch.await_args.args[1:] == ("zone", "Zone C")


# --- names, unique ids and states (historical naming must be kept) ----------


async def test_location_entities_keep_historical_names_and_ids(
    hass: HomeAssistant,
) -> None:
    await _setup(hass, make_entry(), [make_record()])
    registry = er.async_get(hass)

    expected = {
        "vacances_scolaires_location_Paris": (
            "sensor.vacances_scolaires_paris",
            "Vacances Scolaires Paris",
        ),
        "vacances_scolaires_location_Paris_today": (
            "sensor.vacances_scolaires_aujourd_hui_paris",
            "Vacances Scolaires Aujourd'hui Paris",
        ),
        "vacances_scolaires_location_Paris_tomorrow": (
            "sensor.vacances_scolaires_demain_paris",
            "Vacances Scolaires Demain Paris",
        ),
    }
    for unique_id, (entity_id, friendly_name) in expected.items():
        assert registry.async_get_entity_id("sensor", DOMAIN, unique_id) == entity_id
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.attributes["friendly_name"] == friendly_name


async def test_zone_entities_keep_historical_names_and_ids(
    hass: HomeAssistant,
) -> None:
    await _setup(hass, make_zone_entry("Zone C"), [make_record()])
    registry = er.async_get(hass)

    assert (
        registry.async_get_entity_id("sensor", DOMAIN, "vacances_scolaires_zone_Zone C")
        == "sensor.vacances_scolaires_zone_c"
    )
    state = hass.states.get("sensor.vacances_scolaires_zone_c")
    assert state is not None
    assert state.attributes["friendly_name"] == "Vacances Scolaires Zone C"


async def test_entities_belong_to_the_vacances_scolaires_device(
    hass: HomeAssistant,
) -> None:
    entry = make_entry()
    await _setup(hass, entry, [make_record()])
    # async_get_device is deprecated: list the devices of the config entry
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert devices[0].name == "Vacances Scolaires"
    assert (DOMAIN, entry.entry_id) in devices[0].identifiers


async def test_states_while_on_vacation(hass: HomeAssistant) -> None:
    await _setup(hass, make_entry(), [make_record(on_vacation=True)])

    main = hass.states.get("sensor.vacances_scolaires_paris")
    assert main.state == "Zone C - Holidays"
    assert hass.states.get("sensor.vacances_scolaires_aujourd_hui_paris").state == (
        "En vacances"
    )
    assert hass.states.get("sensor.vacances_scolaires_demain_paris").state == (
        "En vacances"
    )


async def test_states_while_at_work(hass: HomeAssistant) -> None:
    await _setup(hass, make_entry(), [make_record(on_vacation=False)])

    main = hass.states.get("sensor.vacances_scolaires_paris")
    assert main.state == "Zone C - Work"
    assert hass.states.get("sensor.vacances_scolaires_aujourd_hui_paris").state == (
        "Pas en vacances"
    )
    assert hass.states.get("sensor.vacances_scolaires_demain_paris").state == (
        "Pas en vacances"
    )


async def test_main_sensor_attributes(hass: HomeAssistant) -> None:
    await _setup(hass, make_entry(), [make_record(description="Vacances de Noël")])

    attrs = hass.states.get("sensor.vacances_scolaires_paris").attributes
    assert attrs["description"] == "Vacances de Noël"
    assert attrs["location"] == "Paris"
    assert attrs["zone"] == "Zone C"
    assert attrs["année_scolaire"] == "2026-2027"
    assert attrs["en_vacances"] is True
    # Dates are exposed as French strings
    assert " à " in attrs["start_date"] and attrs["start_date"].endswith("UTC")
    assert " à " in attrs["end_date"] and attrs["end_date"].endswith("UTC")


async def test_en_vacances_attribute_is_false_at_work(hass: HomeAssistant) -> None:
    await _setup(hass, make_entry(), [make_record(on_vacation=False)])
    attrs = hass.states.get("sensor.vacances_scolaires_paris").attributes
    assert attrs["en_vacances"] is False


# --- selection of the record --------------------------------------------------


async def test_students_record_is_preferred(hass: HomeAssistant) -> None:
    records = [
        make_record(population="Enseignants", description="Enseignants"),
        make_record(population="Élèves", description="Élèves"),
    ]
    entry = make_entry()
    await _setup(hass, entry, records)
    assert entry.runtime_data.data["description"] == "Élèves"


async def test_generic_record_is_used_without_students_record(
    hass: HomeAssistant,
) -> None:
    records = [
        make_record(population="Enseignants", description="Enseignants"),
        make_record(population="-", description="Tous"),
    ]
    entry = make_entry()
    await _setup(hass, entry, records)
    assert entry.runtime_data.data["description"] == "Tous"


async def test_first_record_is_the_last_resort(hass: HomeAssistant) -> None:
    records = [
        make_record(population="Enseignants", description="Premier"),
        make_record(population="Autre", description="Second"),
    ]
    entry = make_entry()
    await _setup(hass, entry, records)
    assert entry.runtime_data.data["description"] == "Premier"


# --- update interval ---------------------------------------------------------


async def test_update_interval_from_entry_data(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 6})
    await _setup(hass, entry, [make_record()])
    assert entry.runtime_data.update_interval == timedelta(hours=6)


async def test_options_take_precedence_over_data(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 6})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={CONF_UPDATE_INTERVAL: 24})
    with patch(FETCH, return_value=[make_record()]):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.runtime_data.update_interval == timedelta(hours=24)


async def test_invalid_stored_interval_is_clamped(hass: HomeAssistant) -> None:
    """An old entry with 0 hours must not make the coordinator loop."""
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 0})
    await _setup(hass, entry, [make_record()])
    assert entry.runtime_data.update_interval == timedelta(hours=1)


async def test_too_large_stored_interval_is_clamped(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 100000})
    await _setup(hass, entry, [make_record()])
    assert entry.runtime_data.update_interval == timedelta(hours=168)


# --- date conversion helper --------------------------------------------------


def test_convert_to_iso_format() -> None:
    assert convert_to_iso_format("17 octobre 2025 à 22:00:00 UTC") == (
        "2025-10-17T22:00:00"
    )
    assert convert_to_iso_format("01 août 2026 à 00:00:00 UTC") == (
        "2026-08-01T00:00:00"
    )


def test_convert_to_iso_format_returns_empty_string_when_malformed() -> None:
    assert convert_to_iso_format("n'importe quoi") == ""
