"""Tests of the options flow."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.vacances_scolaires.const import CONF_UPDATE_INTERVAL

from .common import FETCH, make_entry, make_record


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_options_form_shows_the_current_interval(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 6})
    with patch(FETCH, return_value=[make_record()]):
        await _setup(hass, entry)
        result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["data_schema"]({})[CONF_UPDATE_INTERVAL] == 6


async def test_options_form_clamps_an_invalid_stored_interval(
    hass: HomeAssistant,
) -> None:
    entry = make_entry(**{CONF_UPDATE_INTERVAL: 0})
    with patch(FETCH, return_value=[make_record()]):
        await _setup(hass, entry)
        result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})[CONF_UPDATE_INTERVAL] == 1


async def test_changing_the_interval_reloads_the_entry(hass: HomeAssistant) -> None:
    entry = make_entry()
    with patch(FETCH, return_value=[make_record()]):
        await _setup(hass, entry)
        assert entry.runtime_data.update_interval == timedelta(hours=12)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_UPDATE_INTERVAL: 24}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_UPDATE_INTERVAL] == 24
    assert entry.state is ConfigEntryState.LOADED
    # The entry was reloaded automatically with the new interval
    assert entry.runtime_data.update_interval == timedelta(hours=24)


@pytest.mark.parametrize("interval", [0, -3, 169])
async def test_out_of_range_interval_is_refused(
    hass: HomeAssistant, interval: int
) -> None:
    entry = make_entry()
    with patch(FETCH, return_value=[make_record()]):
        await _setup(hass, entry)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(
                result["flow_id"], {CONF_UPDATE_INTERVAL: interval}
            )
