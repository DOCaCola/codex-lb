## Why

Streamed Claude requests share the model-source header deadline of 20 seconds, which was designed for Responses
sources that answer within milliseconds. Anthropic can hold its response headers until it has processed the prompt,
so a large prompt that misses the cache legitimately takes longer. On 2026-11-28 a 295k-token Codex conversation
failed its compaction seven times in a row with `model_source_timeout` ("Claude did not send response headers within
20s"): every client retry sent the same request and hit the same deadline, so the conversation could not compact.
Over the previous 30 days the deadline also cut about 20 other Claude requests.

The reference gateways give Anthropic far longer: agent-lb 180 s to the first byte, opencodex 200 s for public
upstreams, OmniRoute and sub2api 600 s, and CLIProxyAPI no header bound at all.

## What Changes

- Streamed Claude requests wait up to 180 s for response headers, following agent-lb's Anthropic first-byte budget.
  Connection establishment, the first-frame deadline after headers, the stream idle cap and client cancellation are
  unchanged.
- Model-source timeout messages state the deadline that actually applied instead of the generic constants.

## Impact

- Spec: `claude-accounts`.
- Code: `app/modules/claude/transport.py`, `app/modules/model_sources/forwarding.py`.
- Other model sources keep their deadlines. Antigravity shares the 20 s header deadline and is investigated separately.
