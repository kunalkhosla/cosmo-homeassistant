"""Thin client for the Cosmo parent API.

Auth model (reverse-engineered from the parent web portal):
  * POST /otp/send    {email}        -> emails a one-time code
  * POST /otp/verify  {otp, email}   -> sets an HttpOnly session cookie
  * GET  /otp/refresh                -> renews the cookie (sliding, ~30 min)

There is no bearer token; the session is purely the cookie, so we keep a
private aiohttp CookieJar and persist it across restarts.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import (
    OTP_REFRESH,
    OTP_SEND,
    OTP_VERIFY,
    PARENT_BASE,
    PORTAL_ORIGIN,
    SESSION_TTL_SECONDS,
    WEB_PORTAL_DEVICES,
)

_LOGGER = logging.getLogger(__name__)


class CosmoAuthError(Exception):
    """Raised when the session is invalid and re-login (OTP) is required."""


class CosmoApiError(Exception):
    """Raised for non-auth API failures."""


class CosmoClient:
    """Stateful client holding the session cookie jar."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        # `session` MUST be a private session with its own cookie jar so the
        # Cosmo session cookie never leaks into Home Assistant's shared client.
        self._session = session
        self._expires_at: float = 0.0

    @property
    def _headers(self) -> dict[str, str]:
        # The API is cookie-authed but, like the web app, expects a matching
        # Origin/Referer. Send them to avoid CSRF-style rejections.
        return {
            "Origin": PORTAL_ORIGIN,
            "Referer": f"{PORTAL_ORIGIN}/",
            "Content-Type": "application/json",
        }

    # --- auth -----------------------------------------------------------------

    async def send_otp(self, email: str) -> None:
        """Trigger an email OTP."""
        await self._request("POST", OTP_SEND, json={"email": email}, auth=False)

    async def verify_otp(self, email: str, otp: str) -> dict[str, Any]:
        """Exchange the OTP for a session cookie (stored in the jar)."""
        data = await self._request(
            "POST", OTP_VERIFY, json={"otp": otp, "email": email}, auth=False
        )
        self._mark_refreshed(data)
        return data

    async def refresh(self) -> None:
        """Renew the session cookie. Raises CosmoAuthError if it's dead."""
        data = await self._request("GET", OTP_REFRESH, auth=False)
        self._mark_refreshed(data)

    def _mark_refreshed(self, data: dict[str, Any]) -> None:
        ttl = data.get("expiresIn", SESSION_TTL_SECONDS) if isinstance(data, dict) else SESSION_TTL_SECONDS
        self._expires_at = time.monotonic() + ttl

    @property
    def seconds_until_expiry(self) -> float:
        return max(0.0, self._expires_at - time.monotonic())

    # --- data -----------------------------------------------------------------

    async def get_devices(self) -> list[dict[str, Any]]:
        """List watches on the account (each has imei, username, device_type)."""
        data = await self._request("GET", WEB_PORTAL_DEVICES)
        return data if isinstance(data, list) else []

    async def get_metadata(self, imei: str) -> dict[str, Any]:
        """Last-known location/battery from the SERVER CACHE (no watch wake)."""
        return await self._request(
            "GET", f"{PARENT_BASE}/client-metadata/client/{imei}"
        )

    async def request_fresh_location(self, imei: str) -> dict[str, Any]:
        """ON-DEMAND: ask the watch for a fresh GPS fix. Wakes the watch."""
        return await self._request(
            "GET", f"{PARENT_BASE}/client-metadata/client/{imei}/location"
        )

    async def get_steps(self, imei: str, start: str, end: str) -> int:
        """Total steps over [start, end] (YYYY-MM-DD). Sums per-day rows."""
        data = await self._request(
            "GET",
            f"{PARENT_BASE}/device-steps/client/{imei}",
            params={"startDate": start, "endDate": end},
        )
        if isinstance(data, list):
            return sum(int(row.get("steps", 0) or 0) for row in data)
        return 0

    async def get_call_count(self, imei: str, start: str, end: str) -> dict[str, Any]:
        """{call_count, avg_call_duration} over the date range."""
        return await self._request(
            "GET",
            f"{PARENT_BASE}/call-logs/client/{imei}/count",
            params={"startDate": start, "endDate": end},
        )

    async def get_blocked_calls(self, imei: str, start: str, end: str) -> int:
        """Blocked-call count over the date range."""
        data = await self._request(
            "GET",
            f"{PARENT_BASE}/call-logs/client/{imei}/blocked-calls/count",
            params={"startDate": start, "endDate": end},
        )
        return int(data.get("count", 0)) if isinstance(data, dict) else 0

    async def get_message_summary(self, imei: str, start: str, end: str) -> dict[str, Any]:
        """{totalMessagesSent, uniqueContactsMessaged} over the date range."""
        return await self._request(
            "GET",
            f"{PARENT_BASE}/messages/client/{imei}/summary",
            params={"imei": imei, "startDate": start, "endDate": end},
        )

    # --- transport ------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        try:
            async with self._session.request(
                method, url, json=json, params=params, headers=self._headers
            ) as resp:
                if resp.status in (401, 403):
                    raise CosmoAuthError(f"{method} {url} -> {resp.status}")
                if resp.status >= 400:
                    body = await resp.text()
                    raise CosmoApiError(f"{method} {url} -> {resp.status}: {body[:200]}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except aiohttp.ClientError as err:
            raise CosmoApiError(f"{method} {url} failed: {err}") from err
