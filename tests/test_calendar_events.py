"""Tests of the events exposed by the calendar entity."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant

from custom_components.vacances_scolaires.calendar import (
    VacancesScolairesCalendar,
    convert_to_iso_format,
)
from custom_components.vacances_scolaires.const import DOMAIN

from .common import make_entry

DATA = {
    "on_vacation": True,
    "start_date": "08 novembre 2026 à 00:00:00 UTC",
    "end_date": "15 novembre 2026 à 00:00:00 UTC",
    "description": "Vacances de la Toussaint",
    "location": "Paris",
}


def _calendar(**overrides) -> VacancesScolairesCalendar:
    entry = make_entry()
    coordinator = MagicMock()
    coordinator.config_entry = entry
    coordinator.data = {**DATA, **overrides}
    return VacancesScolairesCalendar(coordinator)


def _utc(year, month, day) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


# --- convert_to_iso_format -------------------------------------------------------


def test_calendar_convert_to_iso_format():
    assert convert_to_iso_format("17 octobre 2025 à 22:00:00 UTC") == (
        "2025-10-17T22:00:00"
    )
    assert convert_to_iso_format("01 août 2026 à 00:00:00 UTC") == (
        "2026-08-01T00:00:00"
    )


# --- identity ----------------------------------------------------------------


def test_calendar_identity():
    calendar = _calendar()
    entry = calendar.coordinator.config_entry

    assert calendar.unique_id == f"{entry.entry_id}_calendar"
    assert calendar.name == "Paris"
    assert calendar.has_entity_name is True
    assert (DOMAIN, entry.entry_id) in calendar.device_info["identifiers"]


# --- current event -----------------------------------------------------------


def test_event_during_the_holidays():
    event = _calendar().event

    assert event is not None
    assert event.summary == "Vacances de la Toussaint"
    assert event.start < event.end
    assert event.start.tzinfo == ZoneInfo("Europe/Paris")
    assert event.end.tzinfo == ZoneInfo("Europe/Paris")


def test_no_event_outside_the_holidays():
    assert _calendar(on_vacation=False).event is None


@pytest.mark.parametrize(
    ("location", "timezone"),
    [
        ("Guadeloupe", "America/Guadeloupe"),
        ("Réunion", "Indian/Reunion"),
        ("Polynésie française", "Pacific/Tahiti"),
    ],
)
def test_event_uses_the_timezone_of_overseas_locations(location, timezone):
    event = _calendar(location=location).event

    assert event is not None
    assert event.start.tzinfo == ZoneInfo(timezone)
    assert event.end.tzinfo == ZoneInfo(timezone)


# --- events in a time frame --------------------------------------------------


async def test_get_events_inside_the_holidays(hass: HomeAssistant) -> None:
    events = await _calendar().async_get_events(
        hass, _utc(2026, 11, 10), _utc(2026, 11, 11)
    )

    assert [event.summary for event in events] == ["Vacances de la Toussaint"]


async def test_get_events_overlapping_the_start_or_the_end(hass: HomeAssistant) -> None:
    calendar = _calendar()

    before = await calendar.async_get_events(
        hass, _utc(2026, 11, 1), _utc(2026, 11, 10)
    )
    after = await calendar.async_get_events(
        hass, _utc(2026, 11, 12), _utc(2026, 11, 30)
    )

    assert len(before) == 1
    assert len(after) == 1


async def test_get_events_containing_the_holidays(hass: HomeAssistant) -> None:
    events = await _calendar().async_get_events(
        hass, _utc(2026, 1, 1), _utc(2026, 12, 31)
    )
    assert len(events) == 1


async def test_get_events_outside_the_holidays(hass: HomeAssistant) -> None:
    calendar = _calendar()

    assert await calendar.async_get_events(hass, _utc(2026, 9, 1), _utc(2026, 10, 1)) == []
    assert await calendar.async_get_events(hass, _utc(2026, 12, 1), _utc(2026, 12, 31)) == []


async def test_get_events_when_not_on_vacation(hass: HomeAssistant) -> None:
    events = await _calendar(on_vacation=False).async_get_events(
        hass, _utc(2026, 11, 10), _utc(2026, 11, 11)
    )
    assert events == []


# --- read only ---------------------------------------------------------------


async def test_calendar_is_read_only() -> None:
    calendar = _calendar()

    with pytest.raises(NotImplementedError):
        await calendar.async_create_event(summary="x")
    with pytest.raises(NotImplementedError):
        await calendar.async_update_event("uid", {})
    with pytest.raises(NotImplementedError):
        await calendar.async_delete_event("uid")
