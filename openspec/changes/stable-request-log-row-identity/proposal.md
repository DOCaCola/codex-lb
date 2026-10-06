## Why
A recovered Claude overload writes two log rows with the same request ID. The dashboard keyed rows and live arrivals by request ID, so React mismatched the duplicates and left orphaned rows stuck above newer entries. The refused rows also had no error code, because Anthropic errors carry only `error.type`.

## What Changes
- The request-log API exposes each row's database ID; the dashboard keys rows and live-arrival tracking by it.
- Model-source failures record the upstream `error.code`, else its `error.type` (for example `overloaded_error`).

## Capabilities
### Modified Capabilities
- `frontend-architecture`: live arrivals and row rendering use log-row identity.
- `provider-request-log-attribution`: provider error classification is recorded.

## Impact
Request-log API schema (new `id` field), dashboard request table, model-source dispatch logging. No migration; existing rows keep their stored error code.
