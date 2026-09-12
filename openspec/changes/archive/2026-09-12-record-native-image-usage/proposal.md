## Why
Native image forwarding settles reported usage against API-key limits but omits that usage from request logs, leaving API-equivalent costs unavailable.

## What Changes
Use a single typed, request-owned image accounting record shared by native dispatch, settlement and request-log persistence. Parse successful upstream usage once before settlement. Preserve unavailable usage as null and retain the existing pricing model.

## Impact
Native image service/route accounting and regression tests. No transport, retry, pricing-rate, database-schema or production configuration change.
