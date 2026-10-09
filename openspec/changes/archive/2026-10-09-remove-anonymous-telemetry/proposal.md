## Why

This fork must never report usage to a third party. Upstream's anonymous telemetry
sends a periodic usage snapshot to `telemetry.tokmaxxing.com`, asks for consent in a
dialog on first visit, and keeps a signing identity in `dashboard_settings`. An opt-out
is not enough for this deployment: the code path, the consent prompt and the stored
identity should not exist.

## What Changes

- **BREAKING** Remove the telemetry capability: the snapshot builder, sender, scheduler,
  consent logic and the `/api/settings/telemetry` endpoints.
- Remove the Settings "Anonymous telemetry" card, the "View collected data" preview and
  the first-visit consent dialog from the dashboard.
- Drop `dashboard_settings.telemetry_consent`, `telemetry_instance_id` and
  `telemetry_private_key_encrypted` in a new migration (the stored private key is
  deleted with them).
- Remove the `telemetry_enabled` and `telemetry_endpoint` settings;
  `CODEX_LB_TELEMETRY_ENABLED` and `CODEX_LB_TELEMETRY_ENDPOINT` join the
  removed-settings warning list. `[settings_fields].max` drops from 97 to 95.
- Remove the telemetry documentation page.

## Capabilities

### Removed Capabilities

- `telemetry`: every requirement is removed; the capability folder is deleted on archive.

### Modified Capabilities

- `configuration-tiers`: examples and scenarios that used telemetry now use settings
  that still exist.
- `frontend-architecture`: the dialog focus-restoration requirement covers only the
  password setup dialog.

## Impact

- Backend: `app/modules/telemetry/` (deleted), `app/main.py`, `app/core/config/settings.py`,
  `app/core/config/tiers.py`, `app/db/models.py`, new Alembic revision.
- Frontend: Settings page, `App.tsx`, settings API/hooks/schemas, test mocks, locales,
  browser smoke.
- Upstream merges: conflicts in these files resolve by keeping telemetry removed.
