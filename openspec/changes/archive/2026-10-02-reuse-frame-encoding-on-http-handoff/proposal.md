# Reuse the frame's encoding when an oversized turn moves to HTTP

## Why

A `response.create` frame above the upstream WebSocket budget is sent over upstream HTTP instead. The frame is already the fully shaped upstream body, but the hand-off parsed it and then serialized the whole HTTP body again, and the transport encoded the frame to UTF-8 twice only to measure it. For a 53.9 MB image-heavy frame that cost about 0.12 s on the event loop per turn, almost all of it re-encoding history that no HTTP rewrite touches. The rewrites that do apply (`type`, `stream`, Responses Lite metadata, instruction normalization) change top-level members or replace the members they change.

## What Changes

- **Members keep their encoding.** The hand-off parses the frame once into its top-level members while recording each member's encoded text. When the HTTP body is serialized, a member whose final value is structurally identical to the parsed one (JSON types kept distinct, so `true` is not `1`) reuses that text. Every other member is encoded as before. The sent body is byte-identical to a full re-serialization for every compact frame the proxy builds.
- **Frame size without a copy.** The transport measures a frame's UTF-8 size from the string itself when it is ASCII, which every `ensure_ascii` frame the proxy builds is, and encodes only non-ASCII text.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: the HTTP hand-off of an oversized frame encodes only the members HTTP shaping changes.

## Impact

- Measured on a 53.9 MB frame: the hand-off drops from about 0.124 s (two size encodes, parse, full re-serialization, body encode) to about 0.046 s (parse, member reuse, body encode). The remaining cost is the single parse the request validation needs.
- The bytes sent upstream are unchanged.
- Not changed: requests through an upstream proxy route, and the Python fallback when the native helper is unavailable, still let their client serialize the body. Neither is configured in production.
