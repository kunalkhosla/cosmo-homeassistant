"""Helpers for the private aiohttp session + cookie persistence.

The Cosmo session is an HttpOnly cookie, so we keep a dedicated CookieJar
(separate from HA's shared client session) and persist it to disk so the
session survives Home Assistant restarts.
"""

from __future__ import annotations

import os

import aiohttp

from homeassistant.core import HomeAssistant


def cookie_path(hass: HomeAssistant, imei: str) -> str:
    """Deterministic per-device cookie file under .storage."""
    return hass.config.path(f".storage/cosmo_{imei}.cookies")


def new_session() -> aiohttp.ClientSession:
    """A private session with its own cookie jar."""
    return aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())


async def load_cookies(hass: HomeAssistant, session: aiohttp.ClientSession, path: str) -> None:
    if await hass.async_add_executor_job(os.path.exists, path):
        await hass.async_add_executor_job(session.cookie_jar.load, path)


async def save_cookies(hass: HomeAssistant, session: aiohttp.ClientSession, path: str) -> None:
    await hass.async_add_executor_job(session.cookie_jar.save, path)
