## Why

Image-heavy Responses turns exceed the WebSocket frame ceiling and upload tens of megabytes over HTTP. The native ChatGPT account path should match the official Codex client's always-on zstd request compression.

## What Changes

- Prepare level-3 zstd bodies once at the shared native-account HTTP `/responses` boundary, off the event loop, for Python and native egress, including account-health probes that use this endpoint.
- Preserve uncompressed payload tracing, body limits, and WebSocket transport selection. Keep model sources, WebSockets, and other upstream endpoints unchanged. Native compaction v2 already targets upstream `/responses`, so it is compressed too; the inbound `/responses/compact` route remains available.
- Surface compression errors and upstream rejection without an uncompressed retry; log sizes and compression duration at DEBUG only.

Reference: OpenAI Codex [`responses_request_compression`](https://github.com/openai/codex/blob/c92700d2993707ee16eb63b35a1cdd7fcc563f69/codex-rs/core/src/client.rs), [Responses endpoint](https://github.com/openai/codex/blob/c92700d2993707ee16eb63b35a1cdd7fcc563f69/codex-rs/codex-api/src/endpoint/responses.rs), and [`prepare_encoded_json`](https://github.com/openai/codex/blob/c92700d2993707ee16eb63b35a1cdd7fcc563f69/codex-rs/http-client/src/request.rs): the `enable_request_compression` feature is stable and on by default, uses level 3 without a threshold, rejects a conflicting Content-Encoding, reuses prepared bytes on retry and never retries uncompressed.

CLIProxyAPI [064e008b](https://github.com/router-for-me/CLIProxyAPI/commit/064e008b) (issue #6905) ships the same compression default-off with a 1 KiB threshold and one uncompressed retry on 400/415. Neither the issue nor the commit records a rejection by the ChatGPT backend; the retry follows the issue's general request for a fallback, and its tests use a mock that rejects on purpose. PR #5132 reports zstd and gzip running against chatgpt.com at about 10k requests a day without rejections. The retry would also resend every genuine 400 uncompressed, so it is not adopted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: native ChatGPT HTTP Responses request compression.

## Impact

Uses the existing Python zstandard dependency. Both aiohttp and Rust egress receive the same compressed bytes and content headers. No configuration, schema, or deployment changes.
