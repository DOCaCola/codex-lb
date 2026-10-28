# Accept native output-token replay

## Why

The affected Codex 0.165 client enabled output-token replay, which requests `output.encrypted_content`
alongside `reasoning.encrypted_content`. The gateway's stale include enum rejects
that request before dispatch with 400 invalid_request_error, param include. A
minimal request reproduces the affected Windows client's exact error over both
HTTP and WebSocket. This is a protocol validation defect, not chat corruption.

## What Changes

- Accept and forward the native output.encrypted_content include value.
- Preserve output-item ciphertext in responses and subsequent native replay.
- Keep explicit rejection of unknown include values and malformed include types.
- Add ingress, forwarding, output and replay regressions on both Responses paths
  and both transports. No feature gate, model substitution or silent stripping.

## Impact

Responses protocol validation. No schema, settings, credentials or history migration.
