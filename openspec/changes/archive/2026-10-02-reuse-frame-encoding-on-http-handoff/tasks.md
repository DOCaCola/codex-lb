## 1. Encoding reuse

- [x] 1.1 `decode_json_object` parses a JSON object once and records each top-level member's encoded text; `encode_json_object` reuses it for structurally identical members
- [x] 1.2 The HTTP hand-off parses the frame with it and passes it to `stream_responses` as `request_body_source`, which encodes the native HTTP body (and the upstream payload trace) from it
- [x] 1.3 `utf8_size` measures frames without encoding ASCII text; the transport measures each frame once

## 2. Verification

- [x] 2.1 Unit tests: decode parity with `json.loads`, rejection of non-objects, member reuse, strict JSON types, non-ASCII members
- [x] 2.2 End-to-end hand-off tests: the native body equals a full re-serialization for unchanged history, normalized history and Responses Lite frames
- [x] 2.3 Full test suite, ruff, ty and the proxy architecture check
