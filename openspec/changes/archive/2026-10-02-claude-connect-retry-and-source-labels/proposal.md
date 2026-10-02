## Why
On 2026-10-02 a ten-second DNS blip produced six `502 model_source_unreachable` failures for one Claude request: the client's attempt and its five automatic retries. Nothing had been sent upstream, so a short gateway retry would have been safe, but the Claude path never retries network errors. Each failure also read "OpenAI-compatible model source request failed", which misattributes Claude and OpenRouter failures.

## What Changes
- Connection failures that prove nothing was dispatched (DNS, refused, connect timeout, proxy connect) are marked as pre-dispatch. TLS verification failures are excluded, because they are stable configuration errors.
- Claude retries pre-dispatch failures on the same account with growing jittered backoff, using the shared four-send budget and the ten-second recovery window. Ambiguous network errors still never replay.
- Model-source error messages name the provider that serves the account: Claude, OpenRouter, or "OpenAI-compatible model source" for generic sources.

## Capabilities
### Modified Capabilities
- `claude-accounts`: bounded pre-dispatch connection recovery.
- `model-source-routing`: provider-attributed error wording.

## Impact
Shared model-source forwarding errors, the Claude transport, and the Claude dispatch loop. No schema or configuration changes.
