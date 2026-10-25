# Scope the Claude Metadata Timeout to Network I/O

## Why

The subscription refresh ran its identity check, a database read, inside the metadata fetch timeout. A timeout
that fired during that read cancelled the query mid-flight and invalidated the database session. The refresh then
raised `PendingRollbackError` instead of recording a timeout, which also stopped the remaining endpoint updates.
That violates the existing rule that one endpoint's failure must not prevent refreshing the others. Production uses
a 60-second timeout, so it was rare; `test_logical_catalog_timeout_does_not_prevent_usage` sets 10 ms and failed
intermittently under full-suite load.

## What Changes

- The metadata fetch timeout covers only the upstream request. The subscription identity check runs after it.

## Impact

- Specs: `claude-accounts` (Coordinated Claude metadata refresh).
- Code: `ClaudeService._refresh_endpoint` in `app/modules/claude/service.py`.
