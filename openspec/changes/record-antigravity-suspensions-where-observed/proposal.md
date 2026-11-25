## Why

Antigravity suspensions could reach the client without holding the account, so later requests kept going to a suspended account.

- **Classification:** a suspension was recognized only by its exact English sentence on a 403. Google's structured signature, `google.rpc.ErrorInfo` with `reason: TOS_VIOLATION`, was ignored. CLIProxyAPI treats that reason as an account-terminal suspension on any HTTP status, including an error frame inside an HTTP 200 stream (CLIProxyAPI #7515, 14cc6ad).
- **Recording:** only retry planning recorded what a rejection proved, and it returned before recording in three cases: once the stream had opened, once the send budget was spent, and once the 429 cap was reached. A streamed response's mid-stream errors, and rejections on later rounds (after a gateway web search or the empty-completion resend), never reached retry planning at all.
- **Web search:** a rejection of the gateway's own search call was turned into a tool error and never recorded.

Recent field reports confirm the state is account-terminal. In sub2api #9009 (Nov 21) three accounts were suspended. In CLIProxyAPI #8021 (Nov 24) a whole pool was suspended, and a minimal neutral request still received the 403. Only Google's appeal restores the account.

## What Changes

- `classify` returns `banned` for ErrorInfo reason `TOS_VIOLATION` regardless of HTTP status or wording. The exact-sentence match remains for bodies without details.
- The transport records every classified rejection for its account where it is observed: on the HTTP response, on the first event, mid-stream, and on later rounds.
- Recovery only plans the next attempt and no longer records anything. Its state drops the generation and families that existed only for recording.
- Gateway web search records account-level holds (ban, location, verification). It does not cool the conversation's quota or model, because the search model's quota is separate.

## Impact

- Spec: `antigravity-accounts`.
- Code: `app/modules/antigravity/classify.py`, `failures.py`, `transport.py`, `recovery.py`, `search.py`, `inference.py`.
- No settings, schema or client changes.
