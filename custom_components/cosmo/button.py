"""Button to request an on-demand fresh GPS fix from the watch.

This is the ONLY action that wakes the watch. It is intentionally never
called on a schedule — press it (or call the cosmo.request_location service
from an automation) when you actually want a live pin.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .api import CosmoApiError
from .entity import CosmoEntity

_LOGGER = logging.getLogger(__name__)

# The watch answers the locate command asynchronously; give it a moment, then
# re-read the server cache so the tracker reflects the fresh fix.
_REFRESH_DELAY = 8


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CosmoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        [CosmoLocateButton(rt.coordinator, entry.data["name"], entry.data.get("model"))]
    )


class CosmoLocateButton(CosmoEntity, ButtonEntity):
    """Request a fresh location now."""

    _attr_translation_key = "request_location"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(self, coordinator, name, model) -> None:
        super().__init__(coordinator, name, model)
        self._attr_unique_id = f"{coordinator.imei}_request_location"

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.request_fresh_location(self.coordinator.imei)
        except CosmoApiError as err:
            _LOGGER.warning("Cosmo locate request failed: %s", err)
            return
        await asyncio.sleep(_REFRESH_DELAY)
        await self.coordinator.async_request_refresh()
