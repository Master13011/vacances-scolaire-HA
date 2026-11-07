"""Helpers shared by the Vacances Scolaires tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vacances_scolaires.const import (
    CONF_CONFIG_TYPE,
    CONF_CREATE_CALENDAR,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    CONF_ZONE,
    DOMAIN,
)

# Where the coordinator looks up the API client (patched in the tests)
FETCH = "custom_components.vacances_scolaires.coordinator.async_fetch_records"


def make_record(
    *,
    on_vacation: bool = True,
    population: str = "-",
    zones: str = "Zone C",
    location: str = "Paris",
    description: str = "Vacances de Test",
) -> dict[str, Any]:
    """Return an API record, currently running or starting in 10 days.

    Dates are relative to now, so the tests do not depend on the calendar.
    """
    now = datetime.now(UTC)
    if on_vacation:
        start, end = now - timedelta(days=2), now + timedelta(days=5)
    else:
        start, end = now + timedelta(days=10), now + timedelta(days=20)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "description": description,
        "location": location,
        "zones": zones,
        "annee_scolaire": "2026-2027",
        "population": population,
    }


def make_entry(**overrides: Any) -> MockConfigEntry:
    """Return a location config entry for Paris (override data as needed)."""
    data: dict[str, Any] = {
        CONF_CONFIG_TYPE: "location",
        CONF_LOCATION: "Paris",
        CONF_UPDATE_INTERVAL: 12,
        CONF_CREATE_CALENDAR: False,
    }
    data.update(overrides)
    return MockConfigEntry(
        domain=DOMAIN,
        title="Vacances Scolaires (Paris)",
        data=data,
        unique_id="location_paris",
    )


def make_zone_entry(zone: str = "Zone C", **overrides: Any) -> MockConfigEntry:
    """Return a zone config entry."""
    data: dict[str, Any] = {
        CONF_CONFIG_TYPE: "zone",
        CONF_ZONE: zone,
        CONF_UPDATE_INTERVAL: 12,
        CONF_CREATE_CALENDAR: False,
    }
    data.update(overrides)
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Vacances Scolaires ({zone})",
        data=data,
        unique_id=f"zone_{zone.lower()}",
    )
