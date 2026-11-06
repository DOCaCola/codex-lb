# Forward the Responses output limit

## Why

codex-lb removed `max_output_tokens` from every request sent to the Codex
backend, because the endpoint used to reject the field at any value (observed
September 28, upstream PR #2496). CLIProxyAPI #7230 (November 3) tested both the
ChatGPT Codex endpoint and Sign in with ChatGPT directly: the field is now
accepted and enforced, ending the response `incomplete` with reason
`max_output_tokens`. `max_tokens` and `max_completion_tokens` remain rejected.

Stripping the limit silently ignores what Responses, `/v1`, Chat and Claude Code
clients ask for. Claude Code's `max_tokens` already includes thinking, as
OpenAI's limit includes reasoning, so the meaning carries over unchanged.
CLIProxyAPI and sub2api forward it; opencodex, OmniRoute and agent-lb still strip it.

## What Changes

- Forward client `max_output_tokens` to the Codex backend unchanged, with no
  floor or adjustment.
- Chat Completions map `max_completion_tokens` (else `max_tokens`) to
  `max_output_tokens` for every route, not only translating adapters.
- Claude Code `max_tokens` reaches the Codex backend as `max_output_tokens`.
- Compact requests keep omitting the limit: a capped compaction would truncate
  the checkpoint that replaces the history.
- Account-neutral replay classification accepts the limit: it bounds output
  and carries no account state, so a goal restart that sets it can still move
  accounts.
- The cache isolation probe treats a stop at its own output limit as a
  measurement, since that terminal frame still reports input usage.
- The Force probe still omits the limit; the requirement no longer claims the
  backend rejects it.

## Impact

Request shaping for Responses, `/v1`, Chat and Messages; cache isolation probe.
Not verified against live upstream servers. If the backend rejected the field
again, the client would receive the upstream 400 unchanged.
