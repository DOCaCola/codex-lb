## 1. Implement

- [x] Prepare level-3 compressed native HTTP Responses bodies off the event loop with correct headers and DEBUG measurements, including compaction v2 and account-health probes.
- [x] Preserve original payload observability and verify Rust egress forwards bytes and headers unchanged.

## 2. Verify

- [x] Cover exact round trips, header handling, native egress, frame-size HTTP fallback, model-source exclusion, and rejection without uncompressed replay.
- [x] Run required pytest suites, lint, formatting, type checking, and strict OpenSpec validation.
