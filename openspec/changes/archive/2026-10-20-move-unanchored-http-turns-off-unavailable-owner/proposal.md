# Move Unanchored HTTP Turns Off an Unavailable Owner

## Why

A resumed thread's first HTTP turn on DOCa Plus failed upstream with `server_error`. The bridge row kept DOCa Plus
and the turn state but no response anchor. The failure put DOCa Plus into a short backoff, and each client retry
carried that turn state, so the bridge required DOCa Plus, refused the switch with `anchor_metadata_missing` and
returned `previous_response_owner_unavailable`. Production saw 24 such refusals in 30 seconds, interleaved with the
same `server_error` whenever the backoff ended, and never tried another account.

Without a response anchor the owner holds no upstream state. A request without `previous_response_id` already
reaches upstream as the client's complete input; the owner is only a routing preference.

## What Changes

- Owner-unavailable recovery treats a durable row without a response anchor, for a request without
  `previous_response_id`, as proof that the non-empty list-shaped input is complete. The request still goes through the
  existing projection and account-neutral validation, and moves to another account through the existing fresh recovery
  lane.
- Anchored rows, including legacy rows without input metadata, keep the existing proof.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: verified full resend recovery from selection-time owner loss.
