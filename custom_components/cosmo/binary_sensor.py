"""Binary sensors: charging, safe-zone, school mode."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .entity import CosmoEntity


@dataclass(frozen=True, kw_only=True)
class CosmoBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[CosmoBinaryDescription, ...] = (
    CosmoBinaryDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("battery_charging"),
    ),
    CosmoBinaryDescription(
        key="safe_zone",
        translation_key="safe_zone",
        icon="mdi:shield-home",
        value_fn=lambda m: m.get("safe_zone"),
    ),
    CosmoBinaryDescription(
        key="school_mode",
        translation_key="school_mode",
        icon="mdi:school",
        value_fn=lambda m: m.get("school_mode"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CosmoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    rt = entry.runtime_data
    async_add_entities(
        CosmoBinarySensor(rt.coordinator, entry.data["name"], entry.data.get("model"), desc)
        for desc in BINARY_SENSORS
    )


class CosmoBinarySensor(CosmoEntity, BinarySensorEntity):
    entity_description: CosmoBinaryDescription

    def __init__(self, coordinator, name, model, description: CosmoBinaryDescription) -> None:
        super().__init__(coordinator, name, model)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.imei}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self._metadata)
