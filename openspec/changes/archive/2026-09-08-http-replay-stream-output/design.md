## Context
The replay store port retained terminal output only; native Responses can supply completed items solely through streamed output_item.done events. Production retained empty output and sent orphaned custom tool results on continuation.

## Decisions
Use a typed per-request collector after downstream duplicate suppression. Match OpenCodex's index ordering, non-empty terminal authority, bounded retention and taint behavior. Bound serialized item data to 8 MiB and 256 items; once tainted, release retained items and decline reconstruction until a fresh lifecycle. HTTP replay persistence consumes and clears the collector. The existing store and owner-based recovery remain unchanged. No database migration, client setting, or production mutation is required.

## Validation
Exercise both tool protocols, incremental and full resends, reconnect/restart, successive HTTP turns and resumed native WebSocket. Unit coverage checks ordering, replacement, malformed indexes, limits, authoritative snapshots, and cleanup.
