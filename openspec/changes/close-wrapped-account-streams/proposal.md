## Why

An account-backed stream holds its account's stream lease until `_stream_with_retry`'s `finally` runs. The proxy consumes it through a chain of async-generator wrappers: error events, rate-limit relay, public normalizer with its reasoning-summary filter, then heartbeat, keepalives and the startup guard. Closing an async generator does not close the iterator it is suspended on. Several wrappers in that chain never closed theirs.

Two cases left the lease held until the abandoned generators were garbage-collected:

- The normalizer raises a 502 `stream_incomplete` from the middle of the chain when a native transport failure reaches it. The wrappers beneath it stay suspended, and the startup guard closes only the normalizer.
- The client closes or abandons the stream early. Closing stops at the first wrapper without a `finally`.

Upstream issue Soju06/codex-lb#2470 measured both stream caps wedging until restart under repeated transport failures, and a balanced acquire/release count after closing the chain. The upstream fix, PR #2616, was closed unmerged. In our production direct HTTP Responses streaming is rare (2 of about 89,000 requests in 7 days), so exposure is low, but the defect applies to every account-backed HTTP stream, including chat completions.

## What Changes

- Every async-generator wrapper between an account-backed stream and the response body closes the stream it wraps when it exits, by completion, error or close. Wrappers covered: error events, rate-limit relay, public normalizer, reasoning-summary filter, the startup-probe prepend helpers and the cursor usage fallback. The keepalive and heartbeat wrappers already did this.
- `_stream_proxy_errors_as_response_failed` returns the error-event generator directly instead of adding an unowned layer.
- The model-source path keeps its explicit layer-by-layer close, which also covers never-started layers.

## Impact

- Spec: `responses-api-compat`.
- Code: `app/modules/proxy/api.py`.
- No settings, schema or client changes.
