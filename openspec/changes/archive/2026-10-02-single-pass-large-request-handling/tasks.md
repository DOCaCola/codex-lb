## 1. Native helper framing

- [x] 1.1 Replace `body`/`text`/`data` command fields with `payload_bytes` and raw trailing bytes; add capability `framed_payload_v1`
- [x] 1.2 Read commands on a dedicated task; validate text payloads as UTF-8
- [x] 1.3 Python adapter writes framed payloads and requires the capability
- [x] 1.4 Rust and Python tests, including a byte-exact framed request body

## 2. Account neutrality at build time

- [x] 2.1 Record split verdicts when bodies are built (`_response_create_text_with_size_guard`, bridge request preparation)
- [x] 2.2 Inherit verdicts across the installation stamp (WebSocket dispatch, HTTP bridge)
- [x] 2.3 Route every neutrality question through the request-state memo; remove the text-only predicate
- [x] 2.4 Drop the fresh-replay fingerprint refresh and the redundant auth replay file-ID parse

## 3. Single-pass fingerprints

- [x] 3.1 `_InputFingerprints` yields prefix and full fingerprints from one pass, byte-identical to `_fingerprint_input_items`
- [x] 3.2 Share it across the retry-safety check, the session anchor, the trimmed and original full fingerprints and bridge request preparation

## 4. Verification

- [x] 4.1 Unit tests for fingerprint equivalence, stamped-verdict recomputation, memo release and the fresh-replay continuity record
- [x] 4.2 Full test suite, ruff, ty, Rust fmt/clippy/tests and real-binary integration tests
