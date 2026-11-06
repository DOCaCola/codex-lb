# Forward public Images requests natively

## Why

`/v1/images/generations` and `/v1/images/edits` were implemented as an
adapter: each request became an internal Responses turn on a chat host model
that forced one `image_generation` tool call. The adapter could not express
what the Images API now offers. It rejected `n > 1`, transparent backgrounds
on `gpt-image-2`, new quality levels and every size outside a local
per-model table. It translated streaming events and spent chat-model quota on
the host turn.

The ChatGPT backend serves the Images API natively at
`/backend-api/codex/images/{generations,edits}`, which codex-lb already
forwards for Codex clients. CLIProxyAPI (`dfe8b182`, November 5) and sub2api
(`c0d511937`) route public Images requests to the same endpoint and pass its
event stream through.

## What Changes

- `/v1/images/*` uses the native forwarding path shared with the Codex routes.
  The request body reaches upstream unchanged apart from the enforced or
  default model (`gpt-image-2`).
- Local per-model validation is removed: `n`, sizes, backgrounds, quality
  levels, output formats and unknown fields are decided upstream.
- Multipart edits are expressed in the native JSON shape: images and mask
  become data URLs, and the Images API numeric and boolean fields are typed.
- A successful native `text/event-stream` response is streamed to the client
  as it arrives. A transport failure between events ends the stream with an
  Images `error` event; one inside an event aborts the connection.
- Usage comes from the native JSON `usage` or the completed stream event and
  settles API-key reservations once.
- The Responses tool adapter, its event translation, internal host selection
  for images and the request-log model rewrite are removed.
- The observability model label accepts any `gpt-image` model ID of the
  documented shape, so new releases need no code change.
- OpenRouter `/v1/images` routing is unchanged.

## Impact

Public `/v1/images/*` behaviour, image request logs and the request-log
repository (the post-insert model rewrite is gone). Codex native image routes
gain streaming. `markup` file parts are not accepted, since their native shape
is undocumented. Not verified against live upstream servers.

