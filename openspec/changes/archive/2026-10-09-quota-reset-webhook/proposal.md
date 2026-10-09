## Why

Operators cannot receive external notification of scheduled or unexpected native
OpenAI quota recovery. Polling dashboards misses short-lived reset opportunities.

## What Changes

Add one disabled-by-default HTTP/HTTPS webhook in Settings. Detect resets from
authoritative usage refreshes, persist transitions atomically, and send one signed
JSON event per account/window through a bounded background delivery worker.

## Capabilities

### Added Capabilities
- `quota-reset-webhook`: quota observation, detection, durable delivery and settings.

## Impact

Usage snapshot persistence, reset-credit intent tracking, dashboard settings,
lifecycle worker, new database tables, security and concurrency tests. No new
environment variables or navigation items. No messaging adapters or batching.
