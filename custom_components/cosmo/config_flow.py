"""Config flow: email + password -> pick watch."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CosmoApiError, CosmoAuthError, CosmoClient
from .const import CONF_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CosmoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Email/password login against the FiLIP backend."""

    VERSION = 2

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip().lower()
            self._password = user_input[CONF_PASSWORD]
            client = CosmoClient(
                async_get_clientsession(self.hass), self._email, self._password
            )
            try:
                await client.login()
                self._devices = await client.get_devices()
            except CosmoAuthError:
                errors["base"] = "invalid_auth"
            except CosmoApiError:
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    return self.async_abort(reason="no_devices")
                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if len(self._devices) == 1:
            return await self._create(self._devices[0])
        if user_input is not None:
            chosen = next(
                d for d in self._devices if str(d["id"]) == user_input[CONF_DEVICE_ID]
            )
            return await self._create(chosen)
        options = {
            str(d["id"]): d.get("firstName") or f"Watch {d['id']}" for d in self._devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}),
        )

    async def _create(self, device: dict[str, Any]) -> ConfigFlowResult:
        device_id = str(device["id"])
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()
        name = device.get("firstName") or "Cosmo Watch"
        return self.async_create_entry(
            title=name,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device_id,
                "name": name,
                "model": device.get("hardwareName"),
            },
        )
