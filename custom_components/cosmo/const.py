"""Constants for the Cosmo (JrTrack kids watch) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "cosmo"

# API hosts (discovered from the Cosmo parent web portal).
ACTIVATION_BASE = "https://activation.api.cosmotogether.com"
PARENT_BASE = "https://parent.api.cosmotogether.com"
PORTAL_ORIGIN = "https://parent.cosmotogether.com"

# Auth (passwordless OTP -> HttpOnly session cookie, ~30 min sliding expiry).
OTP_SEND = f"{ACTIVATION_BASE}/otp/send"
OTP_VERIFY = f"{ACTIVATION_BASE}/otp/verify"
OTP_REFRESH = f"{ACTIVATION_BASE}/otp/refresh"
OTP_LOGOUT = f"{ACTIVATION_BASE}/otp/logout"

# Data endpoints.
WEB_PORTAL_DEVICES = f"{ACTIVATION_BASE}/web-portal/devices"
WEB_PORTAL_PROFILE = f"{ACTIVATION_BASE}/web-portal/profile"

# Session lifetime reported by /otp/verify and /otp/refresh (seconds).
SESSION_TTL_SECONDS = 1800
# Refresh well before expiry to keep the sliding session alive.
REFRESH_MARGIN_SECONDS = 300

# Poll the SERVER CACHE (not the watch) for last-known location/battery.
# This never touches the watch — Cosmo's backend is updated by the watch on
# its own cadence. Safe to poll gently.
DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)
MIN_SCAN_INTERVAL = timedelta(minutes=2)

CONF_EMAIL = "email"
CONF_OTP = "otp"
CONF_IMEI = "imei"
CONF_SCAN_INTERVAL = "scan_interval"

# Service / entity for the ON-DEMAND fresh fix (the only call that wakes the
# watch). Deliberately not on a schedule.
SERVICE_REQUEST_LOCATION = "request_location"

MANUFACTURER = "COSMO Together"
