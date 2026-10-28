# Explicit Claude credential identity replacement

## Why
Reauthorization can return a different provider identity. Operators need to
replace credentials on their existing account entry without losing settings or
statistics, while keeping old provider-owned resources isolated.

## What Changes
- Add explicit replacement consent to credential import and OAuth completion.
- Preserve account configuration/history; reset subscription, quota and cooldown
  observations on identity replacement and advance the identity generation.
- Bind translated replay and native provenance writes to that identity generation.
- Keep strict reconnect as the default and reject stale OAuth completions.

## Impact
Claude account management, native Messages and translated Responses/Chat replay.
Identity generation lives in existing account state; no database migration.
