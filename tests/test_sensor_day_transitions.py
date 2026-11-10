"""Tests of the day sensors when the holidays start or end (today / tomorrow).

The "Aujourd'hui" and "Demain" sensors compare ``now + offset`` with the start
and end of the holidays. These tests freeze the clock around the boundaries to
check that each sensor switches at the right moment:

* "Demain" switches to "En vacances" the day *before* the holidays start,
* "Aujourd'hui" switches to "En vacances" on the first day of the holidays,
* both go back to "Pas en vacances" once the holidays are over.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time

from custom_components.vacances_scolaires.sensor import (
    VacancesScolairesAujourdHuiSensor,
    VacancesScolairesDemainSensor,
)

from .common import make_entry

# Holidays from Sunday 8 November 2026 00:00 to Saturday 14 November 2026 22:00
DATA = {
    "state": "Zone C - Holidays",
    "start_date": "08 novembre 2026 à 00:00:00 UTC",
    "end_date": "14 novembre 2026 à 22:00:00 UTC",
    "description": "Vacances de la Toussaint",
    "location": "Paris",
    "zone": "Zone C",
    "annee_scolaire": "2026-2027",
    "on_vacation": True,
}

HOLIDAYS = "En vacances"
WORK = "Pas en vacances"


def _coordinator(data=DATA) -> MagicMock:
    coordinator = MagicMock()
    coordinator.config_entry = make_entry()
    coordinator.data = data
    return coordinator


def _today(coordinator=None) -> VacancesScolairesAujourdHuiSensor:
    return VacancesScolairesAujourdHuiSensor(coordinator or _coordinator())


def _tomorrow(coordinator=None) -> VacancesScolairesDemainSensor:
    return VacancesScolairesDemainSensor(coordinator or _coordinator())


# --- "Demain": the holidays start tomorrow -------------------------------------


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-11-06 12:00:00", WORK),  # holidays start in two days
        ("2026-11-06 23:59:59", WORK),  # last second before "tomorrow" is the 8th
        ("2026-11-07 00:00:00", HOLIDAYS),  # tomorrow = first moment of the holidays
        ("2026-11-07 12:00:00", HOLIDAYS),  # holidays start tomorrow
        ("2026-11-07 23:59:59", HOLIDAYS),
        ("2026-11-08 12:00:00", HOLIDAYS),  # holidays already started
    ],
)
def test_tomorrow_sensor_around_the_start_of_the_holidays(now, expected):
    with freeze_time(now):
        assert _tomorrow().native_value == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-11-13 12:00:00", HOLIDAYS),  # tomorrow is still the last day
        ("2026-11-13 22:00:00", HOLIDAYS),  # tomorrow = exact end of the holidays
        ("2026-11-14 12:00:00", WORK),  # tomorrow the holidays are over
        ("2026-11-15 12:00:00", WORK),
    ],
)
def test_tomorrow_sensor_around_the_end_of_the_holidays(now, expected):
    with freeze_time(now):
        assert _tomorrow().native_value == expected


# --- "Aujourd'hui": the holidays start today -----------------------------------


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-11-07 12:00:00", WORK),  # the day before
        ("2026-11-07 23:59:59", WORK),  # last second before the holidays
        ("2026-11-08 00:00:00", HOLIDAYS),  # the holidays start today
        ("2026-11-08 12:00:00", HOLIDAYS),
        ("2026-11-11 12:00:00", HOLIDAYS),  # middle of the holidays
    ],
)
def test_today_sensor_around_the_start_of_the_holidays(now, expected):
    with freeze_time(now):
        assert _today().native_value == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-11-14 12:00:00", HOLIDAYS),  # last day
        ("2026-11-14 22:00:00", HOLIDAYS),  # exact end of the holidays
        ("2026-11-14 22:00:01", WORK),  # one second after the end
        ("2026-11-15 12:00:00", WORK),  # the day after
    ],
)
def test_today_sensor_around_the_end_of_the_holidays(now, expected):
    with freeze_time(now):
        assert _today().native_value == expected


# --- both sensors together ---------------------------------------------------------


@pytest.mark.parametrize(
    ("now", "today", "tomorrow"),
    [
        ("2026-11-06 12:00:00", WORK, WORK),
        ("2026-11-07 12:00:00", WORK, HOLIDAYS),  # holidays start tomorrow
        ("2026-11-08 12:00:00", HOLIDAYS, HOLIDAYS),  # holidays start today
        ("2026-11-14 12:00:00", HOLIDAYS, WORK),  # last day: over tomorrow
        ("2026-11-15 12:00:00", WORK, WORK),
    ],
)
def test_day_sensors_over_the_whole_cycle(now, today, tomorrow):
    coordinator = _coordinator()
    with freeze_time(now):
        assert _today(coordinator).native_value == today
        assert _tomorrow(coordinator).native_value == tomorrow


def test_day_sensors_react_to_a_holiday_starting_tomorrow_relative_to_now():
    """Same check without a fixed calendar: dates are built from the real now."""
    from datetime import datetime, timedelta

    def french(moment: datetime) -> str:
        months = [
            "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre",
        ]
        return f"{moment.day:02d} {months[moment.month - 1]} {moment.year} à 00:00:00 UTC"

    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    data = {
        **DATA,
        "start_date": french(today_midnight + timedelta(days=2)),
        "end_date": french(today_midnight + timedelta(days=9)),
    }
    coordinator = _coordinator(data)

    # Holidays start in two days: tomorrow is not a holiday yet at this hour
    with freeze_time(today_midnight + timedelta(hours=12)):
        assert _today(coordinator).native_value == WORK
        assert _tomorrow(coordinator).native_value == WORK
    # One day later, the holidays start tomorrow
    with freeze_time(today_midnight + timedelta(days=1, hours=12)):
        assert _today(coordinator).native_value == WORK
        assert _tomorrow(coordinator).native_value == HOLIDAYS
    # One more day: the holidays start today
    with freeze_time(today_midnight + timedelta(days=2, hours=12)):
        assert _today(coordinator).native_value == HOLIDAYS
        assert _tomorrow(coordinator).native_value == HOLIDAYS


# --- state change at midnight --------------------------------------------------------


def test_sensors_change_state_when_midnight_passes():
    """One sensor instance keeps working across midnight: its value flips."""
    coordinator = _coordinator()
    today, tomorrow = _today(coordinator), _tomorrow(coordinator)

    with freeze_time("2026-11-07 23:59:00"):
        assert today.native_value == WORK
        assert tomorrow.native_value == HOLIDAYS

    with freeze_time("2026-11-08 00:00:05"):
        # The refresh scheduled at 00:00:05 rewrites the state
        for sensor in (today, tomorrow):
            with patch.object(sensor, "async_write_ha_state") as write:
                sensor._handle_midnight_update(MagicMock())
            write.assert_called_once()
        assert today.native_value == HOLIDAYS  # holidays start today
        assert tomorrow.native_value == HOLIDAYS


def test_sensors_change_state_at_the_end_of_the_holidays():
    coordinator = _coordinator()
    today, tomorrow = _today(coordinator), _tomorrow(coordinator)

    with freeze_time("2026-11-14 12:00:00"):  # last day
        assert today.native_value == HOLIDAYS
        assert tomorrow.native_value == WORK

    with freeze_time("2026-11-15 00:00:05"):
        assert today.native_value == WORK
        assert tomorrow.native_value == WORK


def test_day_sensors_use_the_next_holidays_once_the_coordinator_refreshes():
    """When the coordinator switches to the next holidays, both sensors follow."""
    coordinator = _coordinator()
    today, tomorrow = _today(coordinator), _tomorrow(coordinator)

    with freeze_time("2026-12-18 12:00:00"):
        assert today.native_value == WORK
        assert tomorrow.native_value == WORK

        # Christmas holidays start tomorrow (19 December)
        coordinator.data = {
            **DATA,
            "start_date": "19 décembre 2026 à 00:00:00 UTC",
            "end_date": "03 janvier 2027 à 00:00:00 UTC",
        }
        assert today.native_value == WORK
        assert tomorrow.native_value == HOLIDAYS
