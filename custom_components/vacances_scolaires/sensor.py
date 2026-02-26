from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_LOCATION,
    CONF_ZONE,
    CONF_CONFIG_TYPE,
    ATTRIBUTION,
    ATTR_START_DATE,
    ATTR_END_DATE,
    ATTR_DESCRIPTION,
    ATTR_LOCATION,
    ATTR_ZONE,
    ATTR_ANNEE_SCOLAIRE,
    ATTR_EN_VACANCES,
)
from .coordinator import VacancesScolairesDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacances Scolaires sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VacancesScolairesSensor(coordinator, entry),
            VacancesScolairesAujourdHuiSensor(coordinator, entry),
            VacancesScolairesDemainSensor(coordinator, entry),
        ],
        True,
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


class VacancesScolairesSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Vacances Scolaires sensor."""

    def __init__(
        self, coordinator: VacancesScolairesDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        config_type = entry.data.get(CONF_CONFIG_TYPE, "location")
        if config_type == "location":
            location = entry.data.get(CONF_LOCATION, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{location}"
            self._attr_name = f"Vacances Scolaires {location}"
        else:
            zone = entry.data.get(CONF_ZONE, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{zone}"
            self._attr_name = f"Vacances Scolaires {zone}"
        self._attr_attribution = ATTRIBUTION

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("state") if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return {
            ATTR_START_DATE: self.coordinator.data.get("start_date"),
            ATTR_END_DATE: self.coordinator.data.get("end_date"),
            ATTR_DESCRIPTION: self.coordinator.data.get("description"),
            ATTR_LOCATION: self.coordinator.data.get("location"),
            ATTR_ZONE: self.coordinator.data.get("zone"),
            ATTR_ANNEE_SCOLAIRE: self.coordinator.data.get("annee_scolaire"),
            ATTR_EN_VACANCES: self.coordinator.data.get("on_vacation"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Vacances Scolaires",
            manufacturer="Master13011",
            model="API",
        )


class VacancesScolairesAujourdHuiSensor(CoordinatorEntity, SensorEntity):
    """Sensor for 'Are we on vacation today?'."""

    def __init__(
        self, coordinator: VacancesScolairesDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        config_type = entry.data.get(CONF_CONFIG_TYPE, "location")
        if config_type == "location":
            location = entry.data.get(CONF_LOCATION, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{location}_today"
            self._attr_name = f"Vacances Scolaires Aujourd'hui {location}"
        else:
            zone = entry.data.get(CONF_ZONE, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{zone}_today"
            self._attr_name = f"Vacances Scolaires Aujourd'hui {zone}"
        self._attr_attribution = ATTRIBUTION

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        start_date_str = self.coordinator.data.get("start_date")
        end_date_str = self.coordinator.data.get("end_date")
        if not isinstance(start_date_str, str) or not isinstance(end_date_str, str):
            return None
        start_date = datetime.fromisoformat(convert_to_iso_format(start_date_str))
        end_date = datetime.fromisoformat(convert_to_iso_format(end_date_str))
        today = datetime.now()
        return "En vacances" if start_date <= today <= end_date else "Pas en vacances"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return {
            ATTR_START_DATE: self.coordinator.data.get("start_date"),
            ATTR_END_DATE: self.coordinator.data.get("end_date"),
            ATTR_DESCRIPTION: self.coordinator.data.get("description"),
            ATTR_LOCATION: self.coordinator.data.get("location"),
            ATTR_ZONE: self.coordinator.data.get("zone"),
            ATTR_ANNEE_SCOLAIRE: self.coordinator.data.get("annee_scolaire"),
            ATTR_EN_VACANCES: self.coordinator.data.get("on_vacation"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Vacances Scolaires",
            manufacturer="Master13011",
            model="API",
        )


class VacancesScolairesDemainSensor(CoordinatorEntity, SensorEntity):
    """Sensor for 'Are we on vacation tomorrow?'."""

    def __init__(
        self, coordinator: VacancesScolairesDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        config_type = entry.data.get(CONF_CONFIG_TYPE, "location")
        if config_type == "location":
            location = entry.data.get(CONF_LOCATION, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{location}_tomorrow"
            self._attr_name = f"Vacances Scolaires Demain {location}"
        else:
            zone = entry.data.get(CONF_ZONE, "Unknown")
            self._attr_unique_id = f"{DOMAIN}_{config_type}_{zone}_tomorrow"
            self._attr_name = f"Vacances Scolaires Demain {zone}"
        self._attr_attribution = ATTRIBUTION

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        start_date_str = self.coordinator.data.get("start_date")
        end_date_str = self.coordinator.data.get("end_date")
        if not isinstance(start_date_str, str) or not isinstance(end_date_str, str):
            return None
        start_date = datetime.fromisoformat(convert_to_iso_format(start_date_str))
        end_date = datetime.fromisoformat(convert_to_iso_format(end_date_str))
        tomorrow = datetime.now() + timedelta(days=1)
        return (
            "En vacances" if start_date <= tomorrow <= end_date else "Pas en vacances"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return {
            ATTR_START_DATE: self.coordinator.data.get("start_date"),
            ATTR_END_DATE: self.coordinator.data.get("end_date"),
            ATTR_DESCRIPTION: self.coordinator.data.get("description"),
            ATTR_LOCATION: self.coordinator.data.get("location"),
            ATTR_ZONE: self.coordinator.data.get("zone"),
            ATTR_ANNEE_SCOLAIRE: self.coordinator.data.get("annee_scolaire"),
            ATTR_EN_VACANCES: self.coordinator.data.get("on_vacation"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Vacances Scolaires",
            manufacturer="Master13011",
            model="API",
        )
