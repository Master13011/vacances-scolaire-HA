"""Tests of the API client (no network: the HTTP session is faked)."""

from __future__ import annotations

from typing import Any

import aiohttp
import pytest

from custom_components.vacances_scolaires.api import (
    VacancesScolairesApiError,
    VacancesScolairesError,
    VacancesScolairesNoDataError,
    async_fetch_locations,
    async_fetch_records,
    async_fetch_zones,
)


class FakeResponse:
    """Minimal stand-in for an aiohttp response."""

    def __init__(self, status: int = 200, payload: Any = None) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: Any) -> bool:
        return False

    async def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """Minimal stand-in for an aiohttp client session."""

    def __init__(
        self, response: FakeResponse | None = None, error: Exception | None = None
    ) -> None:
        self.response = response
        self.error = error
        self.url: str | None = None
        self.kwargs: dict[str, Any] = {}

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.url = url
        self.kwargs = kwargs
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def ok(payload: Any) -> FakeSession:
    return FakeSession(FakeResponse(200, payload))


# --- async_fetch_records -----------------------------------------------------


async def test_fetch_records_returns_results() -> None:
    session = ok({"results": [{"description": "Vacances"}]})
    assert await async_fetch_records(session, "location", "Paris") == [
        {"description": "Vacances"}
    ]


async def test_fetch_records_builds_query_for_location() -> None:
    session = ok({"results": [{}]})
    await async_fetch_records(session, "location", "Paris")
    params = session.kwargs["params"]
    assert set(params) == {"where", "order_by", "limit", "refine"}
    assert params["refine"] == "location:Paris"
    assert params["order_by"] == "start_date ASC"
    assert params["limit"] == "2"
    assert params["where"].startswith("end_date>=date'")


async def test_fetch_records_builds_query_for_zone() -> None:
    session = ok({"results": [{}]})
    await async_fetch_records(session, "zone", "Zone A", limit=1)
    assert session.kwargs["params"]["refine"] == "zones:Zone A"
    assert session.kwargs["params"]["limit"] == "1"


async def test_fetch_records_value_cannot_inject_query_parameters() -> None:
    evil = "Paris&where=1=1&limit=999"
    session = ok({"results": [{}]})
    await async_fetch_records(session, "location", evil)
    # The value stays inside the single "refine" parameter (aiohttp URL-encodes
    # it) and nothing is appended to the URL by hand.
    assert session.kwargs["params"]["refine"] == f"location:{evil}"
    assert set(session.kwargs["params"]) == {"where", "order_by", "limit", "refine"}
    assert session.url is not None
    assert "?" not in session.url
    assert "&" not in session.url


async def test_fetch_records_does_not_override_ssl_verification() -> None:
    session = ok({"results": [{}]})
    await async_fetch_records(session, "location", "Paris")
    assert "ssl" not in session.kwargs


async def test_fetch_records_rejects_unknown_config_type() -> None:
    with pytest.raises(VacancesScolairesError):
        await async_fetch_records(ok({"results": [{}]}), "nope", "x")


async def test_fetch_records_no_results_raises_no_data() -> None:
    with pytest.raises(VacancesScolairesNoDataError):
        await async_fetch_records(ok({"results": []}), "location", "x")


async def test_fetch_records_missing_results_key_raises_no_data() -> None:
    with pytest.raises(VacancesScolairesNoDataError):
        await async_fetch_records(ok({}), "location", "x")


async def test_fetch_records_http_400_raises_no_data() -> None:
    session = FakeSession(FakeResponse(400, {}))
    with pytest.raises(VacancesScolairesNoDataError):
        await async_fetch_records(session, "location", "x")


async def test_fetch_records_http_500_raises_api_error() -> None:
    session = FakeSession(FakeResponse(500, {}))
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_records(session, "location", "x")


async def test_fetch_records_connection_error_raises_api_error() -> None:
    session = FakeSession(error=aiohttp.ClientError("boom"))
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_records(session, "location", "x")


async def test_fetch_records_timeout_raises_api_error() -> None:
    session = FakeSession(error=TimeoutError())
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_records(session, "location", "x")


async def test_fetch_records_invalid_json_raises_api_error() -> None:
    session = FakeSession(FakeResponse(200, ValueError("bad json")))
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_records(session, "location", "x")


def test_no_data_and_api_errors_are_distinct() -> None:
    """The config flow reports them differently, so they must not overlap."""
    assert not issubclass(VacancesScolairesNoDataError, VacancesScolairesApiError)
    assert not issubclass(VacancesScolairesApiError, VacancesScolairesNoDataError)


# --- async_fetch_locations ---------------------------------------------------


async def test_fetch_locations_dedupes_cleans_and_sorts() -> None:
    session = ok(
        {
            "results": [
                {"location": "Paris"},
                {"location": "aix-Marseille"},
                {"location": None},
                {"location": "   "},
                {"location": "Paris"},
                {"location": "Bordeaux"},
                {},
            ]
        }
    )
    assert await async_fetch_locations(session) == [
        "aix-Marseille",
        "Bordeaux",
        "Paris",
    ]


async def test_fetch_locations_query() -> None:
    session = ok({"results": [{"location": "Paris"}]})
    await async_fetch_locations(session)
    assert session.kwargs["params"] == {
        "select": "location",
        "group_by": "location",
        "limit": "100",
    }


async def test_fetch_locations_empty_raises_no_data() -> None:
    with pytest.raises(VacancesScolairesNoDataError):
        await async_fetch_locations(ok({"results": [{"location": None}]}))


async def test_fetch_locations_http_error_raises_api_error() -> None:
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_locations(FakeSession(FakeResponse(500, {})))


# --- async_fetch_zones -------------------------------------------------------


async def test_fetch_zones_known_zones_first_in_official_order() -> None:
    session = ok(
        {
            "results": [
                {"zones": "Zone C"},
                {"zones": "Réunion"},
                {"zones": "Corse"},
                {"zones": "Nouvelle Zone"},
                {"zones": "Zone A"},
                {"zones": "Zone B"},
            ]
        }
    )
    assert await async_fetch_zones(session) == [
        "Zone A",
        "Zone B",
        "Zone C",
        "Corse",
        "Réunion",
        "Nouvelle Zone",
    ]


async def test_fetch_zones_query() -> None:
    session = ok({"results": [{"zones": "Zone A"}]})
    await async_fetch_zones(session)
    assert session.kwargs["params"] == {
        "select": "zones",
        "group_by": "zones",
        "limit": "100",
    }


async def test_fetch_zones_connection_error_raises_api_error() -> None:
    with pytest.raises(VacancesScolairesApiError):
        await async_fetch_zones(FakeSession(error=aiohttp.ClientError("x")))
