"""Client for the education.gouv.fr school calendar API."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import aiohttp

from .const import CONFIG_TYPE_LOCATION, CONFIG_TYPE_ZONE

API_URL = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "fr-en-calendrier-scolaire/records"
)
API_TIMEOUT = 10

# config type -> dataset field used to filter the records
_REFINE_FIELDS = {
    CONFIG_TYPE_LOCATION: "location",
    CONFIG_TYPE_ZONE: "zones",
}


class VacancesScolairesError(Exception):
    """Base error of the integration's API client."""


class VacancesScolairesApiError(VacancesScolairesError):
    """The API could not be reached or answered with an error."""


class VacancesScolairesNoDataError(VacancesScolairesError):
    """The API answered, but there is no record for this location/zone."""


async def async_fetch_records(
    session: aiohttp.ClientSession,
    config_type: str,
    value: str,
    *,
    limit: int = 2,
) -> list[dict[str, Any]]:
    """Return the next school holidays records for a location or a zone.

    All query parameters are passed through ``params`` so that the user
    supplied ``value`` is always URL-encoded and can never add or alter
    another query parameter.
    """
    field = _REFINE_FIELDS.get(config_type)
    if field is None:
        raise VacancesScolairesError(f"Invalid configuration type: {config_type}")

    params = {
        "where": f"end_date>=date'{date.today().isoformat()}'",
        "order_by": "start_date ASC",
        "limit": str(limit),
        "refine": f"{field}:{value}",
    }

    try:
        async with asyncio.timeout(API_TIMEOUT):
            async with session.get(API_URL, params=params) as response:
                if response.status == 400:
                    # The API rejects values it cannot parse as a facet value
                    raise VacancesScolairesNoDataError(
                        f"Invalid value for {field}: {value}"
                    )
                if response.status != 200:
                    raise VacancesScolairesApiError(
                        f"Error communicating with API: {response.status}"
                    )
                data = await response.json()
    except TimeoutError as err:
        raise VacancesScolairesApiError(
            "Timeout fetching Vacances Scolaires data"
        ) from err
    except (aiohttp.ClientError, ValueError) as err:
        raise VacancesScolairesApiError(
            f"Error communicating with API: {err}"
        ) from err

    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        raise VacancesScolairesNoDataError(f"No data for {field}: {value}")
    return results
