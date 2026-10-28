# Scope and implementation

The normative contract is in [the spec delta](specs/responses-api-compat/spec.md). Compression belongs to native ChatGPT-account HTTP request preparation, not hostname matching or generic egress: source providers and control endpoints must keep their existing protocols. Both streaming and compaction v2 prepare through the same helper before their Python/native/routed dispatch forks. The standalone account-health probe also uses this helper for its streaming `/responses` POST. The existing `/responses/compact` ingress translates to upstream `/responses`; no native upstream `/responses/compact` sender remains in this checkout.

For example, an image-heavy `response.create` still exceeds the WebSocket ceiling based on uncompressed bytes, selects HTTP, and expands conversation history. Its final HTTP JSON is compressed at level 3 in a worker thread. The archive and payload trace retain JSON; only the transport receives compressed bytes. A native helper availability failure can use the existing Python egress fallback with the same compressed byte object. This does not add an uncompressed fallback. A compression failure or HTTP 400/415 remains an error.

Rust source inspection of `crates/codex-lb-egress/src/http.rs` at repository baseline `fac7f2928` shows that `forwarded_headers` appends supplied headers unchanged and `execute_request` passes the supplied bytes to reqwest `.body(body)`. The `.no_zstd()` builder option controls response decoding. No Rust changes are needed. Local wire tests exercise aiohttp and a fake native client against a loopback server; real-worker probes require `CODEX_LB_NATIVE_EGRESS_TEST_BINARY`, and the executable and Cargo toolchain are unavailable in this environment.

# Verification

- The requested proxy/bridge/retry/native suites plus compression, compaction, and Messages model-source tests: 3533 passed, 319 native-worker probes skipped.
- Codex client, encoded JSON, ResponsesTransport, and client-compatibility tests: 96 passed.
- Routed upstream paths and account-probe unit/integration tests: 142 passed.
- `uv run ruff check app tests` and `uv run ruff format --check app tests`: passed.
- `uv run ty check app`: the expected 12 pre-existing diagnostics; no new diagnostics.
- `openspec validate compress-upstream-responses-requests --strict`: passed.
- `openspec validate --specs`: 78 passed, 0 failed.
