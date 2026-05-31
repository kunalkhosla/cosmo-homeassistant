"""Sensors: battery, location, calls, messages, steps."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import CosmoConfigEntry
from .entity import CosmoEntity


@dataclass(frozen=True, kw_only=True)
class CosmoSensorDescription(SensorEntityDescription):
    """A sensor backed by a value extractor over the coordinator data."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _as_dt(value: Any):
    return dt_util.parse_datetime(value) if value else None


SENSORS: tuple[CosmoSensorDescription, ...] = (
    CosmoSensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("metadata", {}).get("battery_level"),
        attrs_fn=lambda d: {
            "charging": d.get("metadata", {}).get("battery_charging"),
            "updated_at": d.get("metadata", {}).get("battery_updated_at"),
        },
    ),
    CosmoSensorDescription(
        key="location_updated_at",
        translation_key="location_updated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _as_dt(d.get("metadata", {}).get("location_updated_at")),
    ),
    CosmoSensorDescription(
        key="address",
        translation_key="address",
        icon="mdi:map-marker",
        value_fn=lambda d: d.get("metadata", {}).get("location"),
    ),
    CosmoSensorDescription(
        key="steps",
        translation_key="steps",
        icon="mdi:shoe-print",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("steps"),
    ),
    CosmoSensorDescription(
        key="calls",
        translation_key="calls",
        icon="mdi:phone",
        native_unit_of_measurement="calls",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("calls", {}).get("call_count"),
        attrs_fn=lambda d: {
            "avg_call_duration": d.get("calls", {}).get("avg_call_duration")
        },
    ),
    CosmoSensorDescription(
        key="blocked_calls",
        translation_key="blocked_calls",
        icon="mdi:phone-cancel",
        native_unit_of_measurement="calls",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("blocked_calls"),
    ),
    CosmoSensorDescription(
        key="messages",
        translation_key="messages",
        icon="mdi:message-text",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("messages", {}).get("totalMessagesSent"),
        attrs_fn=lambda d: {
            "unique_contacts": d.get("messages", {}).get("uniqueContactsMessaged")
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CosmoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        CosmoSensor(rt.coordinator, entry.data["name"], entry.data.get("model"), desc)
        for desc in SENSORS
    )


class CosmoSensor(CosmoEntity, SensorEntity):
    """A single Cosmo metric."""

    entity_description: CosmoSensorDescription

    def __init__(self, coordinator, name, model, description: CosmoSensorDescription) -> None:
        super().__init__(coordinator, name, model)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.imei}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.coordinator.data or {})
        return None
