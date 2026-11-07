"""Vacances Scolaires data coordinator."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    VacancesScolairesError,
    async_fetch_records,
)
from .const import (
    CONF_CONFIG_TYPE,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    CONF_ZONE,
    CONFIG_TYPE_LOCATION,
    CONFIG_TYPE_ZONE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .util import normalize_text, sanitize_update_interval

_LOGGER = logging.getLogger(__name__)

type VacancesScolairesConfigEntry = ConfigEntry[VacancesScolairesDataUpdateCoordinator]


def get_timezone(location: str) -> str:
    timezone_mapping = {
        "Guadeloupe": "America/Guadeloupe",
        "Guyane": "America/Cayenne",
        "Martinique": "America/Martinique",
        "Mayotte": "Indian/Mayotte",
        "Nouvelle Calédonie": "Pacific/Noumea",
        "Polynésie française": "Pacific/Tahiti",
        "Réunion": "Indian/Reunion",
        "Saint Pierre et Miquelon": "America/Miquelon",
        "Wallis et Futuna": "Pacific/Wallis",
    }
    return timezone_mapping.get(location, "Europe/Paris")


def traduire_mois(date_str: str) -> str:
    """Remplace les noms de mois en anglais par leur équivalent français."""
    mois_en = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    mois_fr = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]

    for en, fr in zip(mois_en, mois_fr):
        date_str = date_str.replace(en, fr)

    return date_str


class VacancesScolairesDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Vacances Scolaires data."""

    config_entry: VacancesScolairesConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: VacancesScolairesConfigEntry
    ) -> None:
        """Initialize the data updater."""
        # Options take precedence over the initial data
        hours = config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(hours=sanitize_update_interval(hours)),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        data = self.config_entry.data
        config_type = data.get(CONF_CONFIG_TYPE, CONFIG_TYPE_LOCATION)

        if config_type == CONFIG_TYPE_LOCATION:
            value = data.get(CONF_LOCATION)
        elif config_type == CONFIG_TYPE_ZONE:
            value = data.get(CONF_ZONE)
        else:
            raise UpdateFailed("Invalid configuration type")

        try:
            results = await async_fetch_records(
                async_get_clientsession(self.hass), config_type, value or ""
            )
        except VacancesScolairesError as err:
            raise UpdateFailed(str(err)) from err

        # Filtrer pour prioriser Élèves
        eleves = [
            r for r in results if normalize_text(r.get("population")) == "eleves"
        ]
        tous = [r for r in results if r.get("population") == "-"]

        if eleves:
            result = eleves[0]
        elif tous:
            result = tous[0]
        else:
            # fallback, si vraiment rien trouvé
            result = results[0]

        # Parse dates en datetime avec timezone UTC
        start_date_raw = datetime.fromisoformat(result["start_date"]).replace(
            tzinfo=ZoneInfo("UTC")
        )
        end_date_raw = datetime.fromisoformat(result["end_date"]).replace(
            tzinfo=ZoneInfo("UTC")
        )

        today = datetime.now(ZoneInfo("UTC")).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        on_vacation = start_date_raw <= today <= end_date_raw

        state = (
            f"{result['zones']} - Holidays"
            if on_vacation
            else f"{result['zones']} - Work"
        )

        # Formatage des dates traduites
        start_date_formatted = traduire_mois(
            start_date_raw.strftime("%d %B %Y à %H:%M:%S %Z")
        )
        end_date_formatted = traduire_mois(
            end_date_raw.strftime("%d %B %Y à %H:%M:%S %Z")
        )

        return {
            "state": state,
            "start_date": start_date_formatted,
            "end_date": end_date_formatted,
            "description": result["description"],
            "location": result.get("location"),
            "zone": result.get("zones"),
            "annee_scolaire": result.get("annee_scolaire"),
            "on_vacation": on_vacation,
        }
