# Cosmo Kids Watch — Home Assistant integration

Unofficial Home Assistant integration for the [COSMO JrTrack](https://cosmotogether.com/)
kids smartwatch. It surfaces your child's watch in Home Assistant using the same
cloud API the COSMO parent web portal uses.

> Not affiliated with or endorsed by COSMO Together. Uses a private API that may
> change or break at any time. Use with your own account, at your own risk.

## What you get

A device per watch, with:

| Entity | Type | Notes |
|---|---|---|
| Location | `device_tracker` | Last-known GPS, shown on the HA map. Address, safe-zone & school-mode as attributes. |
| Request location | `button` | On-demand fresh GPS fix — **the only action that wakes the watch**. |
| Battery | `sensor` | % level; charging state & last-update as attributes. |
| Location updated | `sensor` | Timestamp of the last fix. |
| Address | `sensor` | Reverse-geocoded address string. |
| Steps today | `sensor` | Daily step count. |
| Calls today | `sensor` | Call count; average duration as attribute. |
| Calls blocked today | `sensor` | Blocked-call count. |
| Messages today | `sensor` | Messages sent; unique contacts as attribute. |
| Charging / In safe zone / School mode | `binary_sensor` | Status flags. |

### Location history
Home Assistant's recorder stores every location update automatically — so you get
a **location history / breadcrumb trail and timeline that the COSMO portal itself
doesn't offer**. Add a Map card with a history path to see where the watch has been.

## Design: the watch is never polled on a schedule

Home Assistant polls COSMO's **server cache** (`/client-metadata`) on a gentle
interval for last-known location and stats — this never contacts the watch, so it
adds no battery or data load. The watch is only ever woken when you explicitly
press **Request location** (or call the service), so you decide when to spend its
battery on a live fix.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/kunalkhosla/cosmo-homeassistant`, category **Integration**.
2. Install **Cosmo Kids Watch**, then restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → Cosmo Kids Watch**.
4. Enter your COSMO parent-account email, then the one-time code emailed to you.
5. Pick the watch. Done.

## How auth works

The COSMO parent API is passwordless: a one-time code is emailed (`/otp/send` →
`/otp/verify`) and the server returns an HttpOnly session cookie. The integration
stores that cookie and renews it with `/otp/refresh` (~30-minute sliding session),
so you only enter a code once. If the session is ever lost, Home Assistant prompts
you to re-enter a code.

## License

MIT
