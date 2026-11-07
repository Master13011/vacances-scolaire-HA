"""Tests of the calendar platform."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.vacances_scolaires.const import CONF_CREATE_CALENDAR, DOMAIN

from .common import FETCH, make_entry, make_record


async def _setup(hass: HomeAssistant, records):
    entry = make_entry(**{CONF_CREATE_CALENDAR: True})
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=records):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_calendar_is_created_when_requested(hass: HomeAssistant) -> None:
    entry = await _setup(hass, [make_record()])

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "calendar", DOMAIN, f"{entry.entry_id}_calendar"
    )
    assert entity_id == "calendar.vacances_scolaires_paris"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["friendly_name"] == "Vacances Scolaires Paris"


async def test_calendar_is_on_during_holidays(hass: HomeAssistant) -> None:
    await _setup(hass, [make_record(on_vacation=True, description="Vacances")])
    state = hass.states.get("calendar.vacances_scolaires_paris")
    assert state.state == "on"
    assert state.attributes["message"] == "Vacances"


async def test_calendar_is_off_outside_holidays(hass: HomeAssistant) -> None:
    await _setup(hass, [make_record(on_vacation=False)])
    assert hass.states.get("calendar.vacances_scolaires_paris").state == "off"


async def test_calendar_and_sensors_share_the_same_device(
    hass: HomeAssistant,
) -> None:
    from homeassistant.helpers import device_registry as dr

    entry = await _setup(hass, [make_record()])
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
