"""The Cosmo (JrTrack kids watch) integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CosmoApiError, CosmoAuthError, CosmoClient
from .const import (
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import CosmoCoordinator

PLATFORMS = [
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


@dataclass
class CosmoRuntime:
    client: CosmoClient
    coordinator: CosmoCoordinator


CosmoConfigEntry = ConfigEntry[CosmoRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: CosmoConfigEntry) -> bool:
    client = CosmoClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    try:
        await client.login()
    except CosmoAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except CosmoApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = CosmoCoordinator(
        hass, entry, client, entry.data[CONF_DEVICE_ID], DEFAULT_SCAN_INTERVAL
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = CosmoRuntime(client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CosmoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
