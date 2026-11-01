## Why

Dropping the hours from three days on suits things that run out, such as a subscription or a reset credit. A weekly
quota cooldown, though, is planned to the hour: `back in 6d` hides whether it returns this morning or tonight.

## What Changes

- Countdowns know whether they count down to a cooldown or an expiry.
- Cooldowns (5-hour, weekly and API key limit windows) always show days and hours from one day on, e.g. `6d 13h`.
- Expiries (subscription ends, reset-credit expiry) keep showing days only from three days on, e.g. `6d`.
- Below one day both show hours and minutes; below one hour, minutes.

## Capabilities

### Modified Capabilities

- `frontend-architecture`: countdown formatting.
