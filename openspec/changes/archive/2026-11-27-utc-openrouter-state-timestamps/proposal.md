## Why

OpenRouter account pages showed "Catalog updated", "Usage updated" and "Credits updated" one hour off in Berlin. The
service wrote these observation times as naive UTC into the account state, and the state is returned to the dashboard
as stored, so the browser read them as local time. Dashboard response models append the UTC offset only to their own
fields, not to provider state nested inside them. Claude and Antigravity state already store aware UTC times and
display correctly. The new OpenAI API accounts had the same defect in `catalog_updated_at`; that is corrected inside
the unarchived `openai-api-accounts` change, because the feature has not been deployed and no naive values are stored.

## What Changes

- OpenRouter account state requires aware datetimes for its catalog, key and credit observation times, and the
  service writes them as UTC. The catalog refresh schedule compares against aware UTC.
- A data migration rewrites stored naive values as UTC with an explicit offset; its downgrade restores naive UTC for
  older code.

## Impact

- Spec: `openrouter-accounts`.
- Code: `app/modules/openrouter`, `app/modules/proxy/usage_snapshot.py`, Alembic revision
  `20261126_010000_utc_openrouter_state_timestamps`.
- No settings or client changes. The dashboard already parses offset timestamps.
