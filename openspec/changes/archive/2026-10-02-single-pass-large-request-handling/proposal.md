# Encode and inspect large Responses requests once per turn

## Why

Production stalls on 2026-10-02 traced to one image-heavy conversation that resends about 55 MB every turn. Each turn cost about 0.8 s of CPU on the single asyncio event loop, and loop-lag warnings reached 0.61 s and 0.67 s, which delayed every other client sharing the replica. Turns above the 16 MB WebSocket frame budget go over upstream HTTP, so they carry no session anchor, and every one is a full resend.

Most of that time repeated work already done:

- the input history was canonically encoded twice, once for the continuity prefix check and once for the request's own fingerprint;
- the finished body was parsed again up to three times to decide whether it could move accounts;
- a fresh-replay install parsed and re-encoded the body to refresh a fingerprint;
- every native-helper hand-off base64-encoded the body and embedded it in a JSON command line, which was then encoded again.

## What Changes

- **Raw-bytes framing to the native helper.** Commands that carry a body (HTTP request bodies, WebSocket text and binary sends) declare `payload_bytes` on the JSON command line, and exactly that many raw bytes follow. The helper advertises this as the `framed_payload_v1` capability, and the adapter requires it, so an older helper fails negotiation instead of misreading a frame. Base64 and the second JSON encoding are removed. The helper reads commands on a dedicated task because a payload read cannot be cancelled midway.
- **Account-neutrality verdict decided at build time.** The verdict is recorded from the payload dict when the body is serialized. It is split into the body without `client_metadata` and the metadata itself. The installation stamp, the only rewrite between build and dispatch, changes only the metadata, so the stamped body inherits the body verdict and its metadata verdict is recomputed with the same function the stamp applies. The memo is keyed by `str` identity, holds only bodies the request still references, and parses a body it has not seen once.
- **Single-pass input fingerprints.** One canonical encoding pass over the client's input yields both the stored-prefix fingerprint, a hash snapshot after `n` items, and the full fingerprint. The digests are byte-identical to the existing fingerprints, so persisted continuity records stay valid.
- **The fresh-replay install no longer re-fingerprints the sanitized body.** The continuity record keeps describing the client's raw input, which is what the next turn's prefix match compares against.
- **The auth replay switch check no longer parses the fresh body for file IDs.** Neutrality already rejects account-scoped files.

## Capabilities

### Modified Capabilities

- `outbound-http-clients`: native helper command bodies are framed as raw bytes and negotiated through `framed_payload_v1`.
- `responses-api-compat`: request-body inspection (neutrality, fingerprints) is performed once per body.

## Impact

- Measured on a 53 MB anchored WebSocket turn: 8 full passes (0.63 s wall) dropped to 3 (0.29 s). A fresh turn dropped from 4 passes to 3. The HTTP hand-off no longer pays base64 (0.047 s) or the command re-encode (0.096 s).
- The helper binary and the Python adapter must ship together. The image build does this, and a mismatch fails closed at negotiation.
- Not changed: the HTTP hand-off still parses and re-serializes the frame once (about 0.1 s for 53 MB) to apply HTTP-only rewrites.
