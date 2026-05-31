"""Config flow: email -> OTP code -> pick watch."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # noqa: F401

from .api import CosmoApiError, CosmoClient
from .const import CONF_EMAIL, CONF_IMEI, CONF_OTP, DOMAIN
from .session import cookie_path, new_session, save_cookies

_LOGGER = logging.getLogger(__name__)


class CosmoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Cosmo OTP login flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._session = None
        self._client: CosmoClient | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip().lower()
            self._session = new_session()
            self._client = CosmoClient(self._session)
            try:
                await self._client.send_otp(self._email)
            except CosmoApiError:
                errors["base"] = "send_failed"
            else:
                return await self.async_step_otp()
            await self._session.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_EMAIL): str}),
            errors=errors,
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and self._client is not None:
            try:
                await self._client.verify_otp(self._email, user_input[CONF_OTP].strip())
                self._devices = await self._client.get_devices()
            except CosmoApiError:
                errors["base"] = "invalid_code"
            else:
                if not self._devices:
                    return self.async_abort(reason="no_devices")
                return await self.async_step_device()

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required(CONF_OTP): str}),
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # Auto-select when there's a single watch.
        if len(self._devices) == 1:
            return await self._create(self._devices[0])

        if user_input is not None:
            chosen = next(
                d for d in self._devices if d["imei"] == user_input[CONF_IMEI]
            )
            return await self._create(chosen)

        options = {
            d["imei"]: d.get("username") or d.get("device_type") or d["imei"]
            for d in self._devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_IMEI): vol.In(options)}),
        )

    async def _create(self, device: dict[str, Any]) -> ConfigFlowResult:
        imei = device["imei"]
        await self.async_set_unique_id(imei)
        self._abort_if_unique_id_configured()

        # Persist the freshly-minted session cookie so setup can reuse it.
        assert self._session is not None
        await save_cookies(self.hass, self._session, cookie_path(self.hass, imei))
        await self._session.close()

        name = device.get("username") or "Cosmo Watch"
        return self.async_create_entry(
            title=name,
            data={
                CONF_EMAIL: self._email,
                CONF_IMEI: imei,
                "name": name,
                "model": device.get("device_type"),
            },
        )
