"""The Vacances Scolaires integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CREATE_CALENDAR, PLATFORMS
from .coordinator import (
    VacancesScolairesConfigEntry,
    VacancesScolairesDataUpdateCoordinator,
)


def _get_platforms(entry: VacancesScolairesConfigEntry) -> list[Platform]:
    """Return the platforms enabled for this config entry."""
    platforms = list(PLATFORMS)
    if entry.data.get(CONF_CREATE_CALENDAR):
        platforms.append(Platform.CALENDAR)
    return platforms


async def async_setup_entry(
    hass: HomeAssistant, entry: VacancesScolairesConfigEntry
) -> bool:
    """Set up Vacances Scolaires from a config entry."""
    coordinator = VacancesScolairesDataUpdateCoordinator(hass, entry)

    # Raises ConfigEntryNotReady by itself if the first refresh fails
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _get_platforms(entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: VacancesScolairesConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, _get_platforms(entry)
    )
