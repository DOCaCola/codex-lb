# Withdraw the anchor from WebSocket turns sent over HTTP

## Why

A WebSocket `response.create` larger than the upstream frame budget is sent
over HTTP on the same Responses connection (`reason=frame_size`). With
`store=false`, a `previous_response_id` resolves only on the upstream socket
that produced it, and the ChatGPT HTTP backend rejects the field outright
(`Unsupported parameter: previous_response_id`). Production showed five such
failures between 14:14 and 19:41 UTC on November 6, all on image-heavy anchored
turns of 81–88 MB, although the service already held the turn's complete
history.

## What Changes

- At the WebSocket send boundary and the HTTP bridge send boundary, an anchored
  frame that will go over HTTP is replaced by its verified full-history resend
  without `previous_response_id`, built from the same history the replay path
  already uses.
- When no verified full history exists, the turn is refused locally before
  dispatch with `previous_response_not_found`, which Codex answers with a full
  resend. Nothing anchored reaches the HTTP backend.
- The upstream error text is not classified: the fix makes it unreachable.
- Each withdrawal logs `response_create_anchor_withdrawn` with its outcome.

## Impact

WebSocket proxy and HTTP bridge send paths. The resend is larger than the
anchored frame, but it already exceeds the frame budget either way. Not verified
against live upstream servers.
