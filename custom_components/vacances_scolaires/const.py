"""Constants for the Vacances Scolaires integration."""

DOMAIN = "vacances_scolaires"

CONF_LOCATION = "location"
CONF_ZONE = "zone"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_CONFIG_TYPE = "config_type"
CONF_CREATE_CALENDAR = "create_calendar"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_LOCATION = ""
DEFAULT_UPDATE_INTERVAL = 12

PLATFORMS = ["sensor"]

ATTRIBUTION = "Data provided by education.gouv.fr"

ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_DESCRIPTION = "description"
ATTR_LOCATION = "location"
ATTR_ZONE = "zone"
ATTR_ANNEE_SCOLAIRE = "année_scolaire"
ATTR_EN_VACANCES = "en_vacances"

ZONE_OPTIONS = [
    "Zone A",
    "Zone B",
    "Zone C",
    "Corse",
    "Guadeloupe",
    "Guyane",
    "Martinique",
    "Mayotte",
    "Nouvelle Calédonie",
    "Polynésie française",
    "Réunion",
    "Saint Pierre et Miquelon",
    "Wallis et Futuna",
]
