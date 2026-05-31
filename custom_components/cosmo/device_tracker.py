"""Device tracker showing the watch's last-known location on the HA map."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .entity import CosmoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CosmoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        [CosmoTracker(rt.coordinator, entry.data["name"], entry.data.get("model"))]
    )


class CosmoTracker(CosmoEntity, TrackerEntity):
    """The watch as a GPS tracker."""

    _attr_name = None  # use the device name
    _attr_icon = "mdi:watch"

    def __init__(self, coordinator, name, model) -> None:
        super().__init__(coordinator, name, model)
        self._attr_unique_id = f"{coordinator.imei}_tracker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self._metadata.get("latitude")

    @property
    def longitude(self) -> float | None:
        return self._metadata.get("longitude")

    @property
    def extra_state_attributes(self) -> dict:
        m = self._metadata
        return {
            "address": m.get("location"),
            "location_updated_at": m.get("location_updated_at"),
            "safe_zone": m.get("safe_zone"),
            "school_mode": m.get("school_mode"),
        }
