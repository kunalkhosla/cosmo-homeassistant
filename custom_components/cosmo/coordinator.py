"""Data coordinator: polls the server cache, keeps the session alive."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CosmoApiError, CosmoAuthError, CosmoClient
from .const import DOMAIN, REFRESH_MARGIN_SECONDS

_LOGGER = logging.getLogger(__name__)


class CosmoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /client-metadata (server cache) — never wakes the watch."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CosmoClient,
        imei: str,
        scan_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{imei}",
            update_interval=scan_interval,
            config_entry=entry,
        )
        self.client = client
        self.imei = imei

    async def _async_update_data(self) -> dict[str, Any]:
        # Sliding session: refresh the cookie before it lapses. This is a
        # cheap auth call to Cosmo's backend, not a call to the watch.
        try:
            if self.client.seconds_until_expiry < REFRESH_MARGIN_SECONDS:
                await self.client.refresh()

            today = dt_util.now().date().isoformat()
            # All of these read Cosmo's server cache — none wake the watch.
            metadata, calls, blocked, messages, steps = await asyncio.gather(
                self.client.get_metadata(self.imei),
                self.client.get_call_count(self.imei, today, today),
                self.client.get_blocked_calls(self.imei, today, today),
                self.client.get_message_summary(self.imei, today, today),
                self.client.get_steps(self.imei, today, today),
            )
            return {
                "metadata": metadata,
                "calls": calls,
                "blocked_calls": blocked,
                "messages": messages,
                "steps": steps,
            }
        except CosmoAuthError as err:
            raise ConfigEntryAuthFailed(
                "Cosmo session expired; please re-enter a login code"
            ) from err
        except CosmoApiError as err:
            raise UpdateFailed(str(err)) from err
