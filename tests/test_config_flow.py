"""Tests of the config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.vacances_scolaires.api import (
    VacancesScolairesApiError,
    VacancesScolairesNoDataError,
)
from custom_components.vacances_scolaires.const import (
    CONF_CONFIG_TYPE,
    CONF_CREATE_CALENDAR,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    CONF_ZONE,
    DOMAIN,
    ZONE_OPTIONS,
)

from .common import make_entry, make_zone_entry

CF = "custom_components.vacances_scolaires.config_flow"
LOCATIONS = ["Aix-Marseille", "Paris"]
ZONES = ["Zone A", "Zone B", "Zone C", "Corse"]


@pytest.fixture(autouse=True)
def no_real_setup():
    """Do not set the entry up when the flow creates it."""
    with patch(
        "custom_components.vacances_scolaires.async_setup_entry", return_value=True
    ):
        yield


async def _start(hass: HomeAssistant, config_type: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_TYPE: config_type}
    )


def _field(result: dict[str, Any], name: str) -> Any:
    """Return the validator/selector of a form field."""
    for key, value in result["data_schema"].schema.items():
        if key == name:
            return value
    raise AssertionError(f"field {name} not in the form")


# --- location ------------------------------------------------------------------


async def test_location_dropdown_is_filled_from_the_api(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS):
        result = await _start(hass, "location")
    assert result["step_id"] == "location"
    assert list(_field(result, CONF_LOCATION).config["options"]) == LOCATIONS


async def test_location_flow_creates_the_entry(hass: HomeAssistant) -> None:
    with (
        patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS),
        patch(f"{CF}.async_fetch_records", return_value=[{}]),
    ):
        result = await _start(hass, "location")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LOCATION: "Paris",
                CONF_UPDATE_INTERVAL: 12,
                CONF_CREATE_CALENDAR: True,
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vacances Scolaires (Paris)"
    assert result["data"] == {
        CONF_CONFIG_TYPE: "location",
        CONF_LOCATION: "Paris",
        CONF_UPDATE_INTERVAL: 12,
        CONF_CREATE_CALENDAR: True,
    }
    assert result["result"].unique_id == "location_paris"


async def test_location_falls_back_to_free_text_when_list_is_unavailable(
    hass: HomeAssistant,
) -> None:
    with (
        patch(
            f"{CF}.async_fetch_locations",
            side_effect=VacancesScolairesApiError("down"),
        ),
        patch(f"{CF}.async_fetch_records", return_value=[{}]),
    ):
        result = await _start(hass, "location")
        assert result["step_id"] == "location"
        assert _field(result, CONF_LOCATION) is str

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LOCATION: "  Bordeaux  ", CONF_UPDATE_INTERVAL: 12},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LOCATION] == "Bordeaux"  # trimmed


async def test_unknown_location_shows_an_error(hass: HomeAssistant) -> None:
    with (
        patch(
            f"{CF}.async_fetch_locations",
            side_effect=VacancesScolairesNoDataError("none"),
        ),
        patch(
            f"{CF}.async_fetch_records",
            side_effect=VacancesScolairesNoDataError("none"),
        ),
    ):
        result = await _start(hass, "location")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LOCATION: "Atlantide", CONF_UPDATE_INTERVAL: 12},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_LOCATION: "location_not_found"}


async def test_api_down_during_validation_shows_cannot_connect(
    hass: HomeAssistant,
) -> None:
    with (
        patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS),
        patch(
            f"{CF}.async_fetch_records", side_effect=VacancesScolairesApiError("down")
        ),
    ):
        result = await _start(hass, "location")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LOCATION: "Paris", CONF_UPDATE_INTERVAL: 12},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_recovers_after_an_error(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS):
        result = await _start(hass, "location")
        with patch(
            f"{CF}.async_fetch_records", side_effect=VacancesScolairesApiError("down")
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_LOCATION: "Paris", CONF_UPDATE_INTERVAL: 12},
            )
        assert result["errors"] == {"base": "cannot_connect"}
        with patch(f"{CF}.async_fetch_records", return_value=[{}]):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_LOCATION: "Paris", CONF_UPDATE_INTERVAL: 12},
            )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_same_location_cannot_be_added_twice(hass: HomeAssistant) -> None:
    make_entry().add_to_hass(hass)  # unique_id "location_paris"
    with (
        patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS),
        patch(f"{CF}.async_fetch_records", return_value=[{}]),
    ):
        result = await _start(hass, "location")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LOCATION: "Paris", CONF_UPDATE_INTERVAL: 12},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_detection_ignores_case_and_accents(
    hass: HomeAssistant,
) -> None:
    make_entry().add_to_hass(hass)
    with (
        patch(
            f"{CF}.async_fetch_locations",
            side_effect=VacancesScolairesApiError("down"),
        ),
        patch(f"{CF}.async_fetch_records", return_value=[{}]),
    ):
        result = await _start(hass, "location")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LOCATION: "  PARIS ", CONF_UPDATE_INTERVAL: 12},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize("interval", [0, -1, 169])
async def test_location_interval_out_of_range_is_refused(
    hass: HomeAssistant, interval: int
) -> None:
    with (
        patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS),
        patch(f"{CF}.async_fetch_records", return_value=[{}]),
    ):
        result = await _start(hass, "location")
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_LOCATION: "Paris", CONF_UPDATE_INTERVAL: interval},
            )


async def test_location_outside_the_list_is_refused(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS):
        result = await _start(hass, "location")
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_LOCATION: "Atlantide", CONF_UPDATE_INTERVAL: 12},
            )


# --- zone ------------------------------------------------------------------------


async def test_zone_dropdown_is_filled_from_the_api(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_zones", return_value=ZONES):
        result = await _start(hass, "zone")
    assert result["step_id"] == "zone"
    assert list(_field(result, CONF_ZONE).config["options"]) == ZONES


async def test_zone_flow_creates_the_entry(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_zones", return_value=ZONES):
        result = await _start(hass, "zone")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ZONE: "Zone B", CONF_UPDATE_INTERVAL: 6, CONF_CREATE_CALENDAR: False},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vacances Scolaires (Zone B)"
    assert result["data"] == {
        CONF_CONFIG_TYPE: "zone",
        CONF_ZONE: "Zone B",
        CONF_UPDATE_INTERVAL: 6,
        CONF_CREATE_CALENDAR: False,
    }
    assert result["result"].unique_id == "zone_zone b"


async def test_zone_falls_back_to_the_builtin_list(hass: HomeAssistant) -> None:
    with patch(
        f"{CF}.async_fetch_zones", side_effect=VacancesScolairesApiError("down")
    ):
        result = await _start(hass, "zone")
        assert result["step_id"] == "zone"
        assert list(_field(result, CONF_ZONE).config["options"]) == ZONE_OPTIONS

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ZONE: "Zone A", CONF_UPDATE_INTERVAL: 12}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ZONE] == "Zone A"


async def test_same_zone_cannot_be_added_twice(hass: HomeAssistant) -> None:
    make_zone_entry("Zone C").add_to_hass(hass)
    with patch(f"{CF}.async_fetch_zones", return_value=ZONES):
        result = await _start(hass, "zone")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ZONE: "Zone C", CONF_UPDATE_INTERVAL: 12}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_unknown_zone_is_refused(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_zones", return_value=ZONES):
        result = await _start(hass, "zone")
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_ZONE: "Zone Z", CONF_UPDATE_INTERVAL: 12}
            )


@pytest.mark.parametrize("interval", [0, 169])
async def test_zone_interval_out_of_range_is_refused(
    hass: HomeAssistant, interval: int
) -> None:
    with patch(f"{CF}.async_fetch_zones", return_value=ZONES):
        result = await _start(hass, "zone")
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_ZONE: "Zone A", CONF_UPDATE_INTERVAL: interval},
            )


# --- first step --------------------------------------------------------------


async def test_no_ssl_option_is_offered(hass: HomeAssistant) -> None:
    with patch(f"{CF}.async_fetch_locations", return_value=LOCATIONS):
        result = await _start(hass, "location")
    assert "verify_ssl" not in [str(k) for k in result["data_schema"].schema]
