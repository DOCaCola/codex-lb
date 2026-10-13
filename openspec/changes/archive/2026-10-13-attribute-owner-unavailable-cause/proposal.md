## Why
When a previous-response follow-up reaches its owner account and that account rejects it with a quota, rate-limit or overload error, the proxy masks the rejection as a retryable "Previous response owner account is unavailable" error. The masking is deliberate: the Codex client ends the turn on `usage_limit_reached` and quota errors, but retries a retryable server error and then resends the full conversation, which lets the proxy choose another account. On the websocket and HTTP bridge surfaces the mask also drops the cause. The request log row, its upstream error columns and the `continuity_fail_closed` log line do not say which upstream error triggered it, so the dashboard shows a generic owner failure when the account had simply reached its usage limit.

## What Changes
- The client-visible masked error is unchanged: same retryable code, type and generic message, so raw account quota details still do not leak downstream.
- The websocket, HTTP bridge and HTTP stream request log rows record the owner's upstream error code with failure phase `upstream` and failure detail `owner_account_unavailable`.
- The `continuity_fail_closed` diagnostic carries the upstream error code on every surface that masks an owner rejection.
- The dashboard request details show the recorded upstream error code, upstream status and failure stage, so operators see why a request was masked.
- Owner failures detected during account selection, before anything is sent upstream, keep their current message.

## Capabilities
### Modified Capabilities
- `proxy-runtime-observability`: masked owner rejections preserve their upstream cause.

## Impact
Proxy websocket, HTTP bridge and HTTP stream continuity masking, and the dashboard request details dialog. The client-visible error code, type, message and retry behavior are unchanged.
