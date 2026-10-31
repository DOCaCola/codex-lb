## Why

The API Keys page shows one key at a time beside a narrow list, under five overview cards and two lifetime panels.
Comparing keys means clicking through each one, and the list cannot show status, limit progress, recent spend or last
use. A key has no address of its own, so it cannot be linked or opened from elsewhere. Editing happens in a dense
two-column dialog, and Settings › Access edits keys through a second copy of the same dialog.

## What Changes

- `/keys` shows a compact header (key count, active count, 7-day and lifetime cost, Create key), the existing
  comparison chart, then one table of all keys: key (name, prefix, scope), status (active, expiring, limit reached,
  disabled, expired), the first two limit meters, last 7 days (sparkline, cost, tokens), lifetime (cost, share of all
  keys, requests), last used and a row menu. It has search, an All / Active / Needs attention / Disabled & expired
  filter and a sort.
- `/keys/:keyId` and `/keys/:keyId/settings` show one key in the same frame as a provider account: a rail of all
  keys, a header with actions and a ⋯ menu, a state banner, and Overview and Settings tabs. Narrow screens replace the
  rail with a key switcher. An unknown ID shows "API key not found".
- Overview: a Last 7 days card (requests, tokens, cost, last used, and one chart with cost and tokens together), cost
  by account as bars, limits with pooled capacity, access rules and lifetime usage.
- Settings: every field of the edit dialog as full-width cards with one save bar, plus Reset usage and the
  regenerate, enable/disable and delete actions. The edit dialog is removed; Settings › Access opens a key's Settings
  tab instead.
- `/keys?selected=<id>` is not supported.

## Impact

- Affected specs: `frontend-architecture`, `api-keys`
- Affected code: `frontend/src/features/apis`, `frontend/src/features/api-keys`, routes, translations
