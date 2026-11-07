"""Options flow for the Vacances Scolaires integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .util import UPDATE_INTERVAL_VALIDATOR, sanitize_update_interval


class VacancesScolairesOptionsFlowHandler(OptionsFlowWithReload):
    """Handle the options flow for Vacances Scolaires.

    ``OptionsFlowWithReload`` reloads the config entry automatically when the
    options change, so no manual reload is needed.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = sanitize_update_interval(
            self.config_entry.options.get(
                CONF_UPDATE_INTERVAL,
                self.config_entry.data.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL, default=current
                    ): UPDATE_INTERVAL_VALIDATOR,
                }
            ),
        )
