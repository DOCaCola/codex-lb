# Owner quota loss investigation

## Production evidence (2026-10-28, Berlin time)

- 21:51: Andy Alpha (`0aa348`) reached its weekly limit. Its reset is
  2026-11-04 07:35 Berlin (`reset_at` 1793774149). About an hour later Andy
  Beta (`e64fdf`) reached its limit too.
- Anchored turns failed with
  `continuity_fail_closed surface=websocket_connect reason=owner_account_unavailable upstream_error_code=no_accounts`.
  The owner-pinned selection carried no error code and the message
  "Rate limit exceeded. Try again in 300s".
- All 13 affected conversations recovered within 4-44 s. The Codex client
  treats the coded failure as retryable and, after a failure, resends the
  full history without `last_response`. Once the whole pool was spent,
  clients received 429 `usage_limit_reached` with `resets_at`, which was
  correct.

## Client behaviour

`codex-api/src/endpoint/responses_websocket.rs` maps a WebSocket error with
code `previous_response_not_found` to `ApiError::Retryable`, keeping the
server's message. `codex-api/src/sse/responses_error.rs` treats a
`response.failed` with an unrecognized code as retryable as well. The new
code therefore does not change whether the client retries. It makes the
retry semantics explicit and shows the reset time in the client's message.

## References

| Reference | Unservable continuation | Spent quota |
| --- | --- | --- |
| CLIProxyAPI | `previous_response_not_found`: resend the full input without `previous_response_id` | - |
| opencodex | `previous_response_not_found` | `usage_limit_reached` with `resets_at` |
| sub2api | falls back to normal scheduling and drops `previous_response_id` once | - |
| agent-lb, Frozen811 codex-lb | the same generic owner-unavailable message as before this change | - |

codex-lb cannot drop a client anchor silently. A full-history replay is only
possible when the client sent one, and that is already handled by the
retry-safe fresh replay. Reporting the stale-anchor code on the Codex route
follows CLIProxyAPI and opencodex. Reporting the reset follows opencodex.
Owner-only exhaustion must not be reported as pool-wide
`usage_limit_reached`, as the existing "Owner-scoped exhaustion preserves
continuity semantics" scenario requires.
