"""Reverse-geocode the watch's GPS into a human-readable place.

The FiLIP map response gives coordinates but no address, and Home Assistant's
LLM grounding only hands an assistant an entity's *state* (e.g. ``not_home``),
never raw lat/long — so a conversation agent can't say where "away" is. This
turns the coordinates into a short, speakable label (e.g. "Dakota Trail,
Franklin Lakes") via OpenStreetMap's Nominatim, which is free and keyless.

Nominatim is rate-limited (max ~1 req/s) and requires a descriptive User-Agent;
the coordinator only calls this when the rounded coordinates change and polls
every 10 minutes, so usage stays well within their policy.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "cosmo-homeassistant (Home Assistant integration)"


def _short_label(address: dict[str, Any]) -> str:
    """A concise 'street, town' label from Nominatim address components."""
    road = (
        address.get("road")
        or address.get("pedestrian")
        or address.get("neighbourhood")
        or address.get("suburb")
    )
    place = (
        address.get("town")
        or address.get("city")
        or address.get("village")
        or address.get("hamlet")
        or address.get("municipality")
        or address.get("county")
    )
    parts = [p for p in (road, place) if p]
    return ", ".join(parts)


async def reverse_geocode(
    session: aiohttp.ClientSession, lat: float, lon: float
) -> tuple[str | None, str | None]:
    """Return ``(short_label, full_display_name)`` or ``(None, None)`` on failure.

    Defensive by design: any error returns ``(None, None)`` so a geocoding hiccup
    never breaks the location poll.
    """
    params = {
        "format": "jsonv2",
        "lat": f"{lat}",
        "lon": f"{lon}",
        "zoom": "16",
        "addressdetails": "1",
    }
    try:
        async with session.get(
            _URL,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                _LOGGER.debug("nominatim reverse returned HTTP %s", resp.status)
                return None, None
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.debug("nominatim reverse failed: %s", err)
        return None, None

    if not isinstance(data, dict) or "error" in data:
        return None, None
    full = data.get("display_name")
    label = _short_label(data.get("address") or {}) or full
    return label, full
