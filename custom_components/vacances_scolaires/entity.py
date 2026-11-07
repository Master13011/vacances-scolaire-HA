"""Base entity for the Vacances Scolaires integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_CONFIG_TYPE,
    CONF_LOCATION,
    CONF_ZONE,
    CONFIG_TYPE_LOCATION,
    DOMAIN,
)
from .coordinator import (
    VacancesScolairesConfigEntry,
    VacancesScolairesDataUpdateCoordinator,
)


def get_entry_target(entry: VacancesScolairesConfigEntry) -> tuple[str, str]:
    """Return (config type, location or zone name) of a config entry."""
    config_type = entry.data.get(CONF_CONFIG_TYPE, CONFIG_TYPE_LOCATION)
    key = CONF_LOCATION if config_type == CONFIG_TYPE_LOCATION else CONF_ZONE
    return config_type, entry.data.get(key, "Unknown")


class VacancesScolairesEntity(
    CoordinatorEntity[VacancesScolairesDataUpdateCoordinator]
):
    """Base class of all Vacances Scolaires entities."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: VacancesScolairesDataUpdateCoordinator, unique_id: str
    ) -> None:
        """Initialize the entity and attach it to the entry's device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        _, target = get_entry_target(entry)
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Vacances Scolaires {target}",
            manufacturer="Master13011",
            model="API",
        )
