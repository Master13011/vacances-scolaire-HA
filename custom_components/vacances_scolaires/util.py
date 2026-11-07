"""Small helpers shared by the Vacances Scolaires modules."""

from __future__ import annotations

import unicodedata
from typing import Any

import voluptuous as vol

from .const import DEFAULT_UPDATE_INTERVAL, MAX_UPDATE_INTERVAL, MIN_UPDATE_INTERVAL


def normalize_text(text: str | None) -> str:
    """Return the text lower-cased and without accents."""
    if not text:
        return ""
    return (
        unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8")
    ).lower()


def sanitize_update_interval(value: Any) -> int:
    """Return a valid update interval (in hours).

    Protects against invalid values already stored in existing config entries
    (0 or negative values would make the coordinator refresh in a tight loop).
    """
    try:
        hours = int(value)
    except (TypeError, ValueError):
        return DEFAULT_UPDATE_INTERVAL
    return min(max(hours, MIN_UPDATE_INTERVAL), MAX_UPDATE_INTERVAL)


UPDATE_INTERVAL_VALIDATOR = vol.All(
    vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
)
