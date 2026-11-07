"""Client for the education.gouv.fr school calendar API."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import aiohttp

from .const import CONFIG_TYPE_LOCATION, CONFIG_TYPE_ZONE, ZONE_OPTIONS

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


async def _async_get_json(
    session: aiohttp.ClientSession, params: dict[str, str], context: str
) -> Any:
    """GET the records endpoint and return the decoded JSON body."""
    try:
        async with asyncio.timeout(API_TIMEOUT):
            async with session.get(API_URL, params=params) as response:
                if response.status == 400:
                    # The API rejects values it cannot parse as a facet value
                    raise VacancesScolairesNoDataError(f"Invalid query: {context}")
                if response.status != 200:
                    raise VacancesScolairesApiError(
                        f"Error communicating with API: {response.status}"
                    )
                return await response.json()
    except TimeoutError as err:
        raise VacancesScolairesApiError(
            "Timeout fetching Vacances Scolaires data"
        ) from err
    except (aiohttp.ClientError, ValueError) as err:
        raise VacancesScolairesApiError(
            f"Error communicating with API: {err}"
        ) from err


async def _async_fetch_distinct(
    session: aiohttp.ClientSession, field: str
) -> list[str]:
    """Return the distinct, non-empty values of a dataset field."""
    data = await _async_get_json(
        session,
        {"select": field, "group_by": field, "limit": "100"},
        field,
    )
    results = data.get("results") if isinstance(data, dict) else None
    values = {
        r[field].strip()
        for r in results or []
        if isinstance(r, dict) and isinstance(r.get(field), str) and r[field].strip()
    }
    if not values:
        raise VacancesScolairesNoDataError(f"No {field} returned by the API")
    return sorted(values, key=str.casefold)


async def async_fetch_locations(session: aiohttp.ClientSession) -> list[str]:
    """Return the sorted list of locations (academies) known by the API."""
    return await _async_fetch_distinct(session, "location")


async def async_fetch_zones(session: aiohttp.ClientSession) -> list[str]:
    """Return the list of zones known by the API.

    Zones listed in ``ZONE_OPTIONS`` come first, in that order (Zone A, B, C,
    Corse, overseas...), followed by any new zone alphabetically.
    """
    zones = await _async_fetch_distinct(session, "zones")
    return sorted(
        zones,
        key=lambda z: (
            ZONE_OPTIONS.index(z) if z in ZONE_OPTIONS else len(ZONE_OPTIONS),
            z.casefold(),
        ),
    )


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

    data = await _async_get_json(session, params, f"{field}: {value}")

    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        raise VacancesScolairesNoDataError(f"No data for {field}: {value}")
    return results
