## Why

Claude's `/api/oauth/usage` endpoint started answering 429 with a one-hour
Retry-After for our account after its subscription changed, and stayed limited.
codex-lb polled it every three minutes per account even while every inference
reply already carried the same five-hour and weekly figures in its
`anthropic-ratelimit-unified-*` headers.

Claude Code 2.1.285 never polls the endpoint: it reads quota from reply headers,
calls the endpoint only on demand, answers from a header snapshot under 60 seconds
old, and remembers a 429 per access token for its Retry-After (five minutes when
absent, at most one hour). Its User-Agent for this request is the same
`claude-cli/<version> (external, cli)` we send. agent-lb skips its usage poll
while reply headers keep the stored figures fresh; sub2api and opencodex call the
endpoint only on demand; OmniRoute remembers 429s per access token.

Replies also carry the model-scoped weekly window (`7d_oi`, Anthropic's
`seven_day_overage_included`, reported for Fable) and whether extra usage is
being billed (`overage-in-use`). We used `7d_oi` only to classify refusals and
did not show the Fable window at all, although the usage endpoint reports it in
its `limits` list.

## What Changes

- Reply headers are the primary quota source. A scheduled usage read runs only when
  no five-hour or weekly evidence from either source is newer than 15 minutes, or
  when the last successful usage read is an hour old (endpoint-only data: extra
  usage, Opus/Sonnet windows).
- Quota evidence stays fresh for 30 minutes, two idle intervals, so idle accounts
  remain eligible for quota-ranked routing between reads.
- A 429 binds the credential generation that received it: a refreshed token may
  read again once due. Absent or invalid Retry-After hints wait five minutes.
- The `7d_oi` header and the endpoint's Fable `weekly_scoped` limit feed one
  `seven_day_overage_included` window, shown as Weekly Fable, recorded in quota
  history and applied to Fable models.
- `overage-in-use: true` on a reply newer than the last usage read shows the
  extra-usage badge.

## Impact

- Backend: Claude metadata cadence and stored refresh state, header observation,
  quota windows, routing applicability, quota history and trend labels.
- Frontend: Claude window enum and labels.
- Builds on `manual-check-skips-own-backoff`, which must be archived first.
