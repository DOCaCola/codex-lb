# Diagnose Claude reconnect identity mismatches

## Why

Reconnect currently conflates a different authenticated account with a different
organization on the same account. A reported Max-to-Pro resubscription cannot be
diagnosed from this message, and rejected replacement credentials are not retained.

## What Changes

- Distinguish verified account mismatch, verified same-account organization change,
  and an identity mismatch whose saved account UUID is unavailable.
- Return specific dashboard error codes and content-free failure diagnostics for
  both credential import and OAuth reconnect.
- Preserve credentials, ownership and statistics on rejection; retain successful
  same-identity reconnect across expiry and subscription changes.

## Impact

No migration or change to organization ownership policy. Organization migration
remains separate work requiring safe handling of retained server-resource state.
