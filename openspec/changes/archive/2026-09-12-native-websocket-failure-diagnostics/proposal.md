# Native WebSocket failure diagnostics

## Why
Simultaneous native WebSocket receive failures currently discard the phase needed to distinguish local consumer backpressure from helper or upstream transport faults.

## What Changes
Emit one credential-safe warning per failed native WebSocket at the receive adapter boundary, with its opening request ID, allowlisted phase, and local queue name when applicable. No payloads, exception messages, headers, URLs, or success-path logs. Preserve existing client errors and recovery decisions.

## Impact
Native client diagnostics and tests only; no setting, schema migration, or production change.
