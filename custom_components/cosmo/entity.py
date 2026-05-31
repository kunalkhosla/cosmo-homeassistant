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
        d = coordinator.data or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.device_id))},
            name=name,
            manufacturer=MANUFACTURER,
            model=model or "JrTrack",
            sw_version=d.get("firmwareVersion"),
            serial_number=d.get("imei"),
        )

    @property
    def _device(self) -> dict:
        return self.coordinator.data or {}
