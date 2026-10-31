## Why

The Reports page shows a fixed one-hour Claude cache activity table that ignores the report filters and sits apart
from the filtered charts around it. Cache behaviour is already visible per request in the request log and per
conversation in the conversation details, so the table adds noise without a distinct question it answers.

## What Changes

- Remove the Claude cache activity table from the Reports page.
- Remove its `/api/request-logs/claude-cache-activity` endpoint, query and response schemas.

## Impact

- Affected specs: `provider-observability`
- Affected code: `app/modules/request_logs`, `frontend/src/features/reports`, dashboard schemas, translations and
  test fixtures
