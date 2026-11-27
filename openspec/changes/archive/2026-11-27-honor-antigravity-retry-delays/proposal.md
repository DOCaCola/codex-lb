## Why

Antigravity rejections ignored two of Google's retry signals.

- **HTTP `Retry-After`:** classification read the delay only from the body's `google.rpc.RetryInfo`. When Google sent the delay only as a header, a rate limit counted as undelayed, a long delay never counted as quota, and the account was not cooled. Only the unexplained-429 replay read the header, through a separate string path. CLIProxyAPI now falls back to the header after the body, keeping an explicit `0` (CLIProxyAPI #7821, 84b838e).
- **Capacity delays:** an overload (HTTP 503 `UNAVAILABLE`, for example ErrorInfo `MODEL_CAPACITY_EXHAUSTED` with RetryInfo `17s`) was retried after random jitter and recorded nothing, so the next request picked the same model on the same account again. CLIProxyAPI parses the same delay on 503 and cools the model for it (CLIProxyAPI #7957, ae3d80f).
- **Metadata pacing:** a metadata 429 without any delay hint was due again immediately, because the error's retry time defaulted to now. The metadata client also parsed delays separately from classification.

## What Changes

- `classify` takes the raw `Retry-After` header. For 429 and overload answers, RetryInfo wins and the header (delta seconds, an explicit `0`, or an HTTP date) is the fallback. Classification is the only place that turns these signals into a delay, for inference, metadata and web search.
- A bare `RESOURCE_EXHAUSTED` stays `unexplained_429` even with a long header delay, so a content-gated refusal never walks the pool. Its one same-account replay uses the classified delay.
- Recovery waits out an overload delay under 3 seconds on the same account, and otherwise moves once without waiting.
- A rate limit or overload delay of at least 3 seconds cools that model on that account until the delay ends (`rate_limited` or `capacity_exhausted`).
- A rate-limited metadata endpoint waits Google's delay, or its normal interval when Google gives none.

## Impact

- Spec: `antigravity-accounts`.
- Code: `app/modules/antigravity/classify.py`, `recovery.py`, `failures.py`, `transport.py`, `client.py`, `errors.py`, `service.py`, `search.py`.
- No settings, schema or client changes.
