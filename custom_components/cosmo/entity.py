"""Base entity for Cosmo."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CosmoCoordinator


class CosmoEntity(CoordinatorEntity[CosmoCoordinator]):
    """Common device wiring for all Cosmo entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CosmoCoordinator, name: str, model: str | None) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.imei)},
            name=name,
            manufacturer=MANUFACTURER,
            model=model or "JrTrack",
            serial_number=coordinator.imei,
        )

    @property
    def _metadata(self) -> dict:
        return (self.coordinator.data or {}).get("metadata") or {}
