# HTTP fallback replay design

## Reference
OpenCodex `src/responses/state.ts` and `src/server/responses/core.ts` at commit `9a27e86992d7a014e0aa92c046199b9fac148201` provide the input-plus-output retention, output-identity deduplication, bounded spill, and cache-miss recovery behavior adapted here. Native codex-lb upstream WebSocket state remains authoritative for ordinary WebSocket turns.

## Example
An oversized input goes through HTTP with `store=false` and returns a tool call. The client then sends only its response id and a tool result. The proxy retrieves the original input plus completed output, appends the tool result, removes the ephemeral id, and passes the expanded request through normal normalization and routing policy. This preserves images and tool call/result identity. Original client input is retained before upstream item-id normalization so subsequent full resends can match exactly.

## Retention and differences in integration
Small serialized entries are resident within a 64 MiB budget; large entries remain disk-backed. Atomic private files under `<data_dir>/http-fallback-replay` persist both classes, rather than reproducing OpenCodex's separate debounced snapshot and spill-file formats. The one-hour TTL, 1000-entry ceiling, 256 MiB entry ceiling, and 1 GiB disk ceiling apply before replay. Disk budget includes every retained payload file, including resident-entry copies. Periodic ring-heartbeat maintenance also expires idle entries. An advisory SQLite transaction serializes file publication across local workers; it stores no conversation rows and needs no application schema migration.

Conversation content is plaintext in private mode-0600 files in a mode-0700 directory; it is not an archive API or upstream `store=true`. Scope uses the existing conversation identifier or owner-session identifier plus the authenticated API key. Requests without a stable scope do not retain content. Filesystem caches are replica-local unless the deployment shares the data directory; missing state on another replica triggers full client replay.

## Failure modes
Unknown legacy ids retain existing upstream recovery semantics. Known HTTP ids found through request logs cannot establish native response ownership. If replay is expired, corrupt, evicted, or unwritable, Codex-native clients receive the existing sanitized `previous_response_not_found` classifier before upstream dispatch; public clients receive `stream_incomplete`. Successful upstream completions still settle even if cache persistence fails. Failed turns and compaction turns do not seed replay state. Same-model replay retains account preference; model changes rerun normal routing and file ownership checks. Capability lineage still receives the client's original previous id even when replay removes it from the upstream body.

## Verification
Route regressions exercise three HTTP turns across reconnects using both deltas and full resends, followed by a native WebSocket turn. Separate route tests cover native/public cache-miss envelopes and zero upstream calls. Store tests cover exact replay, scope isolation, repeated-message preservation, restart loading, expiry, corruption, memory/disk/count limits, and concurrent publishers.
