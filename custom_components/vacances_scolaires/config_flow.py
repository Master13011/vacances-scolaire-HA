"""Config flow for Vacances Scolaires integration."""

from __future__ import annotations

from typing import Any
from homeassistant.core import callback
import voluptuous as vol
import logging

from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult, FlowContext

from .const import (
    DOMAIN,
    CONF_LOCATION,
    CONF_ZONE,
    CONF_UPDATE_INTERVAL,
    CONF_CONFIG_TYPE,
    CONF_CREATE_CALENDAR,
    DEFAULT_LOCATION,
    DEFAULT_UPDATE_INTERVAL,
    CONF_VERIFY_SSL,
    ZONE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class VacancesScolairesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vacances Scolaires."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult[FlowContext, str]:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_CONFIG_TYPE, default="location"): vol.In(
                            ["location", "zone"]
                        ),
                    }
                ),
            )

        if user_input[CONF_CONFIG_TYPE] == "location":
            return await self.async_step_location()
        else:
            return await self.async_step_zone()

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult[FlowContext, str]:
        """Handle the location step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"Vacances Scolaires ({user_input[CONF_LOCATION]})",
                data={**user_input, CONF_CONFIG_TYPE: "location"},
            )

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION, default=DEFAULT_LOCATION): str,
                    vol.Required(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): int,
                    vol.Optional(CONF_CREATE_CALENDAR, default=False): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult[FlowContext, str]:
        """Handle the zone step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            zone = user_input.get(CONF_ZONE)
            if zone not in ZONE_OPTIONS:
                errors[CONF_ZONE] = "invalid_zone"
            else:
                return self.async_create_entry(
                    title=f"Vacances Scolaires ({zone})",
                    data={**user_input, CONF_CONFIG_TYPE: "zone"},
                )

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE, default=ZONE_OPTIONS[0]): vol.In(
                        ZONE_OPTIONS
                    ),
                    vol.Required(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): int,
                    vol.Optional(CONF_CREATE_CALENDAR, default=False): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        from .options_flow import VacancesScolairesOptionsFlowHandler

        return VacancesScolairesOptionsFlowHandler(config_entry