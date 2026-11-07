"""Sensor platform of the Vacances Scolaires integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change

from .const import (
    ATTR_ANNEE_SCOLAIRE,
    ATTR_DESCRIPTION,
    ATTR_END_DATE,
    ATTR_EN_VACANCES,
    ATTR_LOCATION,
    ATTR_START_DATE,
    ATTR_ZONE,
    DOMAIN,
)
from .coordinator import (
    VacancesScolairesConfigEntry,
    VacancesScolairesDataUpdateCoordinator,
)
from .entity import VacancesScolairesEntity, get_entry_target


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VacancesScolairesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacances Scolaires sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            VacancesScolairesSensor(coordinator),
            VacancesScolairesAujourdHuiSensor(coordinator),
            VacancesScolairesDemainSensor(coordinator),
        ]
    )


def convert_to_iso_format(date_str: str) -> str:
    """Convertit une date au format '28 mai 2025 à 22:00:00 UTC' en ISO '2025-05-28T22:00:00'."""
    mois = {
        "janvier": "01",
        "février": "02",
        "mars": "03",
        "avril": "04",
        "mai": "05",
        "juin": "06",
        "juillet": "07",
        "août": "08",
        "septembre": "09",
        "octobre": "10",
        "novembre": "11",
        "décembre": "12",
    }

    parts = date_str.split(" ")
    if len(parts) < 6:
        return ""

    day, month_str, year, _, time_str, _ = parts
    month = mois.get(month_str.lower(), "01")
    return f"{year}-{month}-{day}T{time_str}"


class VacancesScolairesSensorBase(VacancesScolairesEntity, SensorEntity):
    """Common behaviour of the Vacances Scolaires sensors."""

    # Suffix appended to the historical unique_id (kept unchanged so that
    # existing entities are not recreated).
    _unique_id_suffix = ""

    def __init__(self, coordinator: VacancesScolairesDataUpdateCoordinator) -> None:
        config_type, target = get_entry_target(coordinator.config_entry)
        super().__init__(
            coordinator,
            f"{DOMAIN}_{config_type}_{target}{self._unique_id_suffix}",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        data = self.coordinator.data
        return {
            ATTR_START_DATE: data.get("start_date"),
            ATTR_END_DATE: data.get("end_date"),
            ATTR_DESCRIPTION: data.get("description"),
            ATTR_LOCATION: data.get("location"),
            ATTR_ZONE: data.get("zone"),
            ATTR_ANNEE_SCOLAIRE: data.get("annee_scolaire"),
            ATTR_EN_VACANCES: data.get("on_vacation"),
        }


class VacancesScolairesSensor(VacancesScolairesSensorBase):
    """Main sensor: current or next school holidays."""

    _attr_name = None  # use the device name
    _attr_translation_key = "vacances_scolaires"
    _attr_icon = "mdi:school"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("state") if self.coordinator.data else None


class VacancesScolairesDaySensor(VacancesScolairesSensorBase):
    """Sensor telling whether a given day (today, tomorrow...) is a holiday."""

    _day_offset = 0

    async def async_added_to_hass(self) -> None:
        """Register midnight update callback."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._handle_midnight_update,
                hour=0,
                minute=0,
                second=5,
            )
        )

    @callback
    def _handle_midnight_update(self, now: datetime) -> None:
        """Force state refresh at midnight."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        start_date_str = self.coordinator.data.get("start_date")
        end_date_str = self.coordinator.data.get("end_date")
        if not isinstance(start_date_str, str) or not isinstance(end_date_str, str):
            return None
        try:
            start_date = datetime.fromisoformat(convert_to_iso_format(start_date_str))
            end_date = datetime.fromisoformat(convert_to_iso_format(end_date_str))
        except ValueError:
            return None
        target = datetime.now() + timedelta(days=self._day_offset)
        return "En vacances" if start_date <= target <= end_date else "Pas en vacances"


class VacancesScolairesAujourdHuiSensor(VacancesScolairesDaySensor):
    """Sensor for 'Are we on vacation today?'."""

    _day_offset = 0
    _unique_id_suffix = "_today"
    _attr_name = "Aujourd'hui"
    _attr_icon = "mdi:calendar-today"


class VacancesScolairesDemainSensor(VacancesScolairesDaySensor):
    """Sensor for 'Are we on vacation tomorrow?'."""

    _day_offset = 1
    _unique_id_suffix = "_tomorrow"
    _attr_name = "Demain"
    _attr_icon = "mdi:calendar-arrow-right"
