"""The Cosmo (JrTrack kids watch) integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import CosmoApiError, CosmoAuthError, CosmoClient
from .const import CONF_IMEI, DEFAULT_SCAN_INTERVAL
from .coordinator import CosmoCoordinator
from .session import cookie_path, load_cookies, new_session, save_cookies

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


@dataclass
class CosmoRuntime:
    """Per-entry runtime objects."""

    client: CosmoClient
    coordinator: CosmoCoordinator
    session: object  # aiohttp.ClientSession


CosmoConfigEntry = ConfigEntry[CosmoRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: CosmoConfigEntry) -> bool:
    """Set up Cosmo from a config entry."""
    imei = entry.data[CONF_IMEI]

    session = new_session()
    await load_cookies(hass, session, cookie_path(hass, imei))
    client = CosmoClient(session)

    # Validate / renew the persisted session up front.
    try:
        await client.refresh()
    except CosmoAuthError as err:
        await session.close()
        raise ConfigEntryAuthFailed(
            "Stored Cosmo session expired; please re-authenticate"
        ) from err
    except CosmoApiError as err:
        await session.close()
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = CosmoCoordinator(
        hass, entry, client, imei, DEFAULT_SCAN_INTERVAL
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = CosmoRuntime(client, coordinator, session)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CosmoConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and entry.runtime_data:
        # Save the (refreshed) cookie so the next start reuses the live session.
        await save_cookies(
            hass,
            entry.runtime_data.session,
            cookie_path(hass, entry.data[CONF_IMEI]),
        )
        await entry.runtime_data.session.close()
    return unloaded
