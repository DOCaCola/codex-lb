## Implementation

- [x] Add bounded, cancellation-owned HTTP event relay to the upstream Responses connection.
- [x] Replace upstream byte-limit refusal and history slimming with per-turn transport selection.
- [x] Normalize provider HTTP 413 to a terminal context overflow event.
- [x] Verify transport selection, payload preservation, account routing, continuation, and teardown.
- [x] Sync and validate specifications; archive after verification.

## Verification

- 1,367 unit tests passed across proxy utilities, WebSocket client, transport adapter, HTTP bridge payload handling, cancellation, and transport observability.
- After the final pending-close race fix, all eight transport adapter tests and both changed WebSocket route regressions passed again. New HTTP turns cannot dispatch behind a pending upstream close.
- All 134 WebSocket integration tests passed; the changed oversized/input-preservation cases passed again after final adapter changes.
- Direct and routed HTTP 413 tests passed, including propagate-status callers.
- Ruff lint and formatting, ty checks on changed application modules, cancellation safety, and proxy architecture checks passed.
- All 58 specs passed the CI-pinned OpenSpec 1.11.0 validation command. The changed capability and change passed strict validation. Repository-wide strict validation additionally flags 22 pre-existing placeholder-purpose warnings in unrelated capabilities.
- Main specifications were synced before archive. Tests use controlled upstreams; no production deployment or live model requests were performed.
