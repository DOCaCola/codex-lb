# Oversized WebSocket turns over HTTP

## Why

A Responses create frame can exceed the upstream WebSocket byte ceiling while remaining valid over HTTP. Returning 413 makes Codex repeat the same request before disabling WebSocket for its session.

## What Changes

- Select HTTP SSE for oversized upstream create frames before sending, retaining the downstream WebSocket and all input.
- Reuse account routing, authentication, settlement, and response event handling across transports.
- Keep later small turns eligible for WebSocket.
- Represent upstream HTTP 413 as terminal context_length_exceeded to prevent transport retries.

## Impact

Responses transport adapters, size preflight, regression coverage, and responses-api-compat specifications. No deployment or client configuration changes.
