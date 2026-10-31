## Why

Cloud Code answers some requests with a bare `429 RESOURCE_EXHAUSTED` whatever the account's quota; the refusal
follows the request content (OmniRoute #18140, CLIProxyAPI #5751, #6280). Our recovery already spends at most one
same-account retry on it and never walks the pool. The client then receives a 429, and most clients resend a 429:
Claude Code and the OpenAI and Anthropic SDKs retry it with backoff, and Codex retries any 429 that carries a retry
delay. Every resend reaches Google with the same refused content, the pattern OmniRoute observed getting accounts
flagged.

OmniRoute (ea5814d2) answers identical resends locally from an in-memory fingerprint store for 2 to 30 minutes. The
clients that resend already honour a standard signal to stop: Claude Code and both SDKs do not retry a response
carrying `x-should-retry: false` (Claude Code's gateway documentation recommends it for this case), and Codex treats
a 429 without a retry delay as final. Reporting the refusal as final removes the resend at its source without
request memory.

## What Changes

- An unexplained Antigravity 429 reported to the client carries `x-should-retry: false` and no `Retry-After`.
- Google's `Retry-After` header still sets the delay of the single same-account retry.

## Impact

- Affected specs: `antigravity-accounts`
- Affected code: `app/modules/antigravity/recovery.py`
