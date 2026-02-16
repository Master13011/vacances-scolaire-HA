from datetime import timedelta, date, datetime
import logging
from typing import Any
import asyncio
from zoneinfo import ZoneInfo
import aiohttp
import unicodedata

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_LOCATION, CONF_ZONE, CONF_CONFIG_TYPE, CONF_UPDATE_INTERVAL, CONF_VERIFY_SSL

_LOGGER = logging.getLogger(__name__)

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
        "Wallis et Futuna": "Pacific/Wallis"
    }
    return timezone_mapping.get(location, "Europe/Paris")

def traduire_mois(date_str: str) -> str:
    """Remplace les noms de mois en anglais par leur équivalent français."""
    mois_en = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
    mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

    for en, fr in zip(mois_en, mois_fr):
        date_str = date_str.replace(en, fr)

    return date_str

def normalize_population(pop: str | None) -> str:
    """Normalise le champ population (minuscules + sans accents)."""
    if not pop:
        return ""
    pop_norm = unicodedata.normalize("NFD", pop).encode("ascii", "ignore").decode("utf-8")
    return pop_norm.lower()

class VacancesScolairesDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Vacances Scolaires data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the data updater."""
        self.entry = entry  # Stocker la ConfigEntry
        self.config = entry.data  # Données de configuration initiales
        self.options = entry.options  # Options modifiables après configuration

        # Récupération dynamique de l'intervalle (options priorisées sur data)
        hours_val = (
            self.options.get(CONF_UPDATE_INTERVAL)
            if self.options and CONF_UPDATE_INTERVAL in self.options
            else self.config.get(CONF_UPDATE_INTERVAL, 12)
        )

        if hours_val is None:
            hours_int = 12
        else:
            try:
                hours_int = int(hours_val)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Valeur d'intervalle invalide ({hours_val}), utilisation de 12 heures par défaut")
                hours_int = 12

        update_interval = timedelta(hours=hours_int)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        verify_ssl = self.entry.options.get(
            CONF_VERIFY_SSL,
            self.config.get(CONF_VERIFY_SSL, True)
        )
        _LOGGER.debug(f"Appel API avec verify_ssl={verify_ssl}")

        today_str = date.today().isoformat()
        config_type = self.config.get(CONF_CONFIG_TYPE, "location")

        if config_type == "location":
            location = self.config.get(CONF_LOCATION)
            api_url = (
                f"https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/"
                f"records?where=end_date%3E%3Ddate%27{today_str}%27&order_by=start_date%20ASC&limit=2&refine=location%3A{location}"
            )
        elif config_type == "zone":
            zone = self.config.get(CONF_ZONE)
            api_url = (
                f"https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/"
                f"records?where=end_date%3E%3Ddate%27{today_str}%27&order_by=start_date%20ASC&limit=2&refine=zones%3A{zone}"
            )
        else:
            raise UpdateFailed("Invalid configuration type")

        try:
            async with asyncio.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, ssl=verify_ssl) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"Error communicating with API: {response.status}")
                        data = await response.json()
                        
                        if not data.get("results"):
                            raise UpdateFailed("No data received from API")
                        
                        results = data.get("results", [])

                        # Filtrer pour prioriser Élèves
                        eleves = [r for r in results if normalize_population(r.get("population")) == "eleves"]
                        tous = [r for r in results if r.get("population") == "-"]
                        
                        if eleves:
                            result = eleves[0]
                        elif tous:
                            result = tous[0]
                        else:
                            # fallback, si vraiment rien trouvé
                            result = results[0] if results else None
                        
                        if not result:
                            raise UpdateFailed("No suitable vacation data found")

                        # Parse dates en datetime avec timezone UTC
                        start_date_raw = datetime.fromisoformat(result['start_date']).replace(tzinfo=ZoneInfo("UTC"))
                        end_date_raw = datetime.fromisoformat(result['end_date']).replace(tzinfo=ZoneInfo("UTC"))

                        today = datetime.now(ZoneInfo("UTC")).replace(hour=0, minute=0, second=0, microsecond=0)
                        on_vacation = start_date_raw <= today <= end_date_raw

                        state = f"{result['zones']} - Holidays" if on_vacation else f"{result['zones']} - Work"

                        # Formatage des dates traduites
                        start_date_formatted = traduire_mois(start_date_raw.strftime("%d %B %Y à %H:%M:%S %Z"))
                        end_date_formatted = traduire_mois(end_date_raw.strftime("%d %B %Y à %H:%M:%S %Z"))

                        return {
                            "state": state,
                            "start_date": start_date_formatted,
                            "end_date": end_date_formatted,
                            "description": result['description'],
                            "location": result.get('location'),
                            "zone": result.get('zones'),
                            "annee_scolaire": result.get('annee_scolaire'),
                            "on_vacation": on_vacation
                        }
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout fetching Vacances Scolaires data")
