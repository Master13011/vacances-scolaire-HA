"""Config flow for the Vacances Scolaires integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    VacancesScolairesApiError,
    VacancesScolairesError,
    VacancesScolairesNoDataError,
    async_fetch_locations,
    async_fetch_records,
    async_fetch_zones,
)
from .const import (
    CONF_CONFIG_TYPE,
    CONF_CREATE_CALENDAR,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    CONF_ZONE,
    CONFIG_TYPE_LOCATION,
    CONFIG_TYPE_ZONE,
    DEFAULT_LOCATION,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ZONE_OPTIONS,
)
from .util import UPDATE_INTERVAL_VALIDATOR, normalize_text

_LOGGER = logging.getLogger(__name__)

class VacancesScolairesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vacances Scolaires."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        # None = not fetched yet, [] = API unavailable (fallback to free text
        # for locations, to the built-in list for zones)
        self._locations: list[str] | None = None
        self._zones: list[str] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_CONFIG_TYPE, default=CONFIG_TYPE_LOCATION
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=[CONFIG_TYPE_LOCATION, CONFIG_TYPE_ZONE],
                                translation_key=CONF_CONFIG_TYPE,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
            )

        if user_input[CONF_CONFIG_TYPE] == CONFIG_TYPE_LOCATION:
            return await self.async_step_location()
        return await self.async_step_zone()

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the location step."""
        errors: dict[str, str] = {}
        session = async_get_clientsession(self.hass)

        if self._locations is None:
            try:
                self._locations = await async_fetch_locations(session)
            except VacancesScolairesError as err:
                _LOGGER.debug("Cannot fetch the locations list: %s", err)
                self._locations = []

        if user_input is not None:
            location = user_input[CONF_LOCATION].strip()
            try:
                # Always checked, even with the dropdown (cheap and safe)
                await async_fetch_records(
                    session, CONFIG_TYPE_LOCATION, location, limit=1
                )
            except VacancesScolairesNoDataError:
                errors[CONF_LOCATION] = "location_not_found"
            except VacancesScolairesApiError as err:
                _LOGGER.debug("Cannot validate location %s: %s", location, err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{CONFIG_TYPE_LOCATION}_{normalize_text(location)}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Vacances Scolaires ({location})",
                    data={
                        **user_input,
                        CONF_LOCATION: location,
                        CONF_CONFIG_TYPE: CONFIG_TYPE_LOCATION,
                    },
                )

        defaults = user_input or {}
        location_field: Any
        if self._locations:
            location_field = SelectSelector(
                SelectSelectorConfig(
                    options=self._locations,
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=False,
                )
            )
            default_location = defaults.get(CONF_LOCATION)
            if default_location not in self._locations:
                default_location = vol.UNDEFINED
        else:
            location_field = str
            default_location = defaults.get(CONF_LOCATION, DEFAULT_LOCATION)

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION, default=default_location): location_field,
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=defaults.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): UPDATE_INTERVAL_VALIDATOR,
                    vol.Optional(
                        CONF_CREATE_CALENDAR,
                        default=defaults.get(CONF_CREATE_CALENDAR, False),
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the zone step."""
        if self._zones is None:
            try:
                self._zones = await async_fetch_zones(
                    async_get_clientsession(self.hass)
                )
            except VacancesScolairesError as err:
                _LOGGER.debug("Cannot fetch the zones list: %s", err)
                self._zones = []

        zones = self._zones or ZONE_OPTIONS

        if user_input is not None:
            zone = user_input[CONF_ZONE]
            await self.async_set_unique_id(
                f"{CONFIG_TYPE_ZONE}_{normalize_text(zone)}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Vacances Scolaires ({zone})",
                data={**user_input, CONF_CONFIG_TYPE: CONFIG_TYPE_ZONE},
            )

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE, default=zones[0]): SelectSelector(
                        SelectSelectorConfig(
                            options=zones,
                            mode=SelectSelectorMode.DROPDOWN,
                            custom_value=False,
                        )
                    ),
                    vol.Required(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): UPDATE_INTERVAL_VALIDATOR,
                    vol.Optional(CONF_CREATE_CALENDAR, default=False): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        from .options_flow import VacancesScolairesOptionsFlowHandler

        return VacancesScolairesOptionsFlowHandler()
