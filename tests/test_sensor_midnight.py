"""The day sensors must flip when the 00:00:05 refresh fires, not before.

``native_value`` of the "Aujourd'hui" / "Demain" sensors is computed on the fly,
so reading it with a frozen clock would pass even if the midnight refresh were
removed. What the user sees is the state *written* in Home Assistant, and it is
only rewritten by the coordinator or by the ``async_track_time_change`` callback
registered at 00:00:05. These tests therefore go through a real setup and fire
the time change, then read ``hass.states``.

The dates are the ones the API really sends: the holidays of the Toussaint 2026
start on Sunday 8 November at 00:00 in Paris, i.e. 22:00 UTC the evening before,
and the last day ends at 22:00 UTC.
"""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .common import FETCH, make_entry

TODAY = "sensor.vacances_scolaires_aujourd_hui_paris"
TOMORROW = "sensor.vacances_scolaires_demain_paris"

HOLIDAYS = "En vacances"
WORK = "Pas en vacances"

RECORD = {
    "start_date": "2026-11-07T22:00:00+00:00",
    "end_date": "2026-11-14T22:00:00+00:00",
    "description": "Vacances de la Toussaint",
    "location": "Paris",
    "zones": "Zone C",
    "annee_scolaire": "2026-2027",
    "population": "-",
}


def _states(hass: HomeAssistant) -> tuple[str, str]:
    return hass.states.get(TODAY).state, hass.states.get(TOMORROW).state


async def _midnight(hass: HomeAssistant, freezer, moment: str) -> None:
    """Move the clock to ``moment`` (UTC) and fire the time change."""
    freezer.move_to(f"{moment}+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_day_sensors_flip_when_the_midnight_refresh_fires(
    hass: HomeAssistant, freezer
) -> None:
    # Sensors use the naive local time, frozen as UTC: align Home Assistant on it
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-11-06 12:00:00+00:00")
    entry = make_entry()
    entry.add_to_hass(hass)

    with patch(FETCH, return_value=[RECORD]):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Holidays start in two days
        assert _states(hass) == (WORK, WORK)

        # The clock passes midnight but the refresh has not fired yet:
        # the written state has not changed.
        freezer.move_to("2026-11-07 00:00:05+00:00")
        assert _states(hass) == (WORK, WORK)

        # 00:00:05 on the 7th: the holidays start tomorrow
        await _midnight(hass, freezer, "2026-11-07 00:00:05")
        assert _states(hass) == (WORK, HOLIDAYS)

        # 00:00:05 on the 8th: the holidays start today
        await _midnight(hass, freezer, "2026-11-08 00:00:05")
        assert _states(hass) == (HOLIDAYS, HOLIDAYS)

        # 00:00:05 on the 14th (last day): the 15th is a school day
        await _midnight(hass, freezer, "2026-11-14 00:00:05")
        assert _states(hass) == (HOLIDAYS, WORK)

        # 00:00:05 on the 15th: the holidays are over
        await _midnight(hass, freezer, "2026-11-15 00:00:05")
        assert _states(hass) == (WORK, WORK)
