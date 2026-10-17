# Resume Deferred Claude Search

## Why

When Claude calls web search and a client tool in the same response, Anthropic defers the search: the response stops
with `tool_use`, carries the `server_tool_use` without a result, and runs the search after the client returns its tool
results; the result then opens the next response (Anthropic server-tools documentation, "Mixing server tools and client
tools in one turn"). The translated adapter treats every pending search as malformed output. Production recorded ten
such failures in fourteen days ("Claude stopped with unfinished output (open=none, pending_search=1,
stop_reason=tool_use)"), all on Opus 5.5; one conversation failed seven consecutive retries because the same request
deterministically produced the same deferral.

Third-party evidence: opencodex #7194 suppresses a deferred search and lists its resume as unimplemented (#7205);
vercel/ai #13533 and vellum-assistant #42901 resume it by replaying the call and returning only tool results;
coder/xum #6210 documents the 400 that follows when the resuming user message carries anything else.

## What Changes

- A translated response that stops with `tool_use` and contains a client tool call completes. Each pending search is
  delivered as a done `web_search_call` with status `in_progress`, followed by a reasoning item whose authenticated
  opaque state holds only the search call. Without a client tool call, a pending search still fails.
- Replay restores a deferred call ahead of the client tool calls of its assistant turn. When the request continues the
  turn with only tool results and still declares search, the call is forwarded so Anthropic runs it; the projection
  hands the call to the response translator, which accepts the result opening the response and stores the call and
  result as an ordinary search pair for the original search item.
- An unanswered deferred call that can no longer run (interrupted turn, other content in the resuming message, later
  history, search no longer declared) is omitted and logged as `claude_deferred_search_omitted`.
- Account replay, OpenAI handoff and readable projections treat an answered deferred search as one completed search and
  omit an unanswered one. Active deferred search stays bound to its account and model, as active search is today.

## Capabilities

### Modified Capabilities

- `claude-accounts`: Codex protocol adaptation; translated hosted web search.
