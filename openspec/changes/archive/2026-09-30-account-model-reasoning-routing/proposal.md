# Proposal

## Why

Operators need model-specific reasoning eligibility without changing client requests. Temporary entitlement loss must not erase their saved configuration.

## What Changes

- Add optional per-account, per-model reasoning allowlists; unrestricted means all supported efforts, including future levels.
- Apply reasoning eligibility before priority, affinity and warm transport reuse; preserve strict ownership.
- Keep unavailable saved models editable in configuration but absent from client discovery and routing.
- Move All models into each conversation-model dialog and save mode, selections and reasoning together.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-model-controls`: reasoning eligibility, unavailable selections and dialog-local mode controls.

## Impact

Native account persistence/migration, provider state and projection, HTTP/WS selection and reuse, discovery, shared model dialogs and regression tests. No production configuration or client payload rewriting.
