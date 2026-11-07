"""Vacances Scolaires Calendar platform."""

from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import (
    VacancesScolairesConfigEntry,
    VacancesScolairesDataUpdateCoordinator,
    get_timezone,
)
from .entity import VacancesScolairesEntity

# Fonction pour convertir la date dans le bon format et ajouter un fuseau horaire
def convert_to_iso_format(date_str: str, location: str | None = None) -> str:
    # Créer un dictionnaire pour les mois en français
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

    # Extraire les parties de la date
    day, month_str, year, _, time_str, _ = date_str.split(" ")

    # Convertir le mois en chiffre
    month = mois[month_str.lower()]

    # Créer la chaîne avec le format ISO attendu
    iso_format_date = f"{year}-{month}-{day}T{time_str}"

    # Retourner la date au format ISO
    return iso_format_date


class VacancesScolairesCalendar(VacancesScolairesEntity, CalendarEntity):
    """Vacances Scolaires Calendar class."""

    _attr_name = None  # use the device name

    def __init__(self, coordinator: VacancesScolairesDataUpdateCoordinator) -> None:
        # The unique_id is unchanged so that existing calendars are kept.
        super().__init__(coordinator, f"{coordinator.config_entry.entry_id}_calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if self.coordinator.data["on_vacation"]:
            start_date_str = self.coordinator.data["start_date"]
            end_date_str = self.coordinator.data["end_date"]
            location = self.coordinator.data[
                "location"
            ]  # Localisation pour déterminer le fuseau horaire

            # Récupérer le fuseau horaire correspondant à la localisation
            timezone = get_timezone(location)  # Utiliser le fuseau horaire dynamique

            # Convertir les dates en datetime et appliquer le fuseau horaire
            start_date = datetime.fromisoformat(
                convert_to_iso_format(start_date_str, location)
            ).astimezone(ZoneInfo(timezone))
            end_date = datetime.fromisoformat(
                convert_to_iso_format(end_date_str, location)
            ).astimezone(ZoneInfo(timezone))

            return CalendarEvent(
                start=start_date,
                end=end_date,
                summary=self.coordinator.data["description"],
            )
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        events = []
        if self.coordinator.data["on_vacation"]:
            start_date_str = self.coordinator.data["start_date"]
            end_date_str = self.coordinator.data["end_date"]
            location = self.coordinator.data[
                "location"
            ]  # Localisation pour déterminer le fuseau horaire

            # Récupérer le fuseau horaire correspondant à la localisation
            timezone = get_timezone(location)  # Utiliser le fuseau horaire dynamique

            # Convertir les dates en datetime et appliquer le fuseau horaire
            event_start = datetime.fromisoformat(
                convert_to_iso_format(start_date_str, location)
            ).astimezone(ZoneInfo(timezone))
            event_end = datetime.fromisoformat(
                convert_to_iso_format(end_date_str, location)
            ).astimezone(ZoneInfo(timezone))

            if start_date <= event_end and end_date >= event_start:
                event = CalendarEvent(
                    start=event_start,
                    end=event_end,
                    summary=self.coordinator.data["description"],
                )
                events.append(event)
        return events

    async def async_create_event(self, **kwargs: Any) -> None:
        raise NotImplementedError

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None
    ) -> None:
        raise NotImplementedError

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None
    ) -> None:
        raise NotImplementedError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VacancesScolairesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacances Scolaires Calendar platform."""
    async_add_entities([VacancesScolairesCalendar(entry.runtime_data)])
