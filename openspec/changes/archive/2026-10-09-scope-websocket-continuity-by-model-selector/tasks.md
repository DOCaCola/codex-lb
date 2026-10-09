## 1. Contract

- [x] 1.1 Define exact-model-selector ownership for proxy-injected WebSocket
  continuity anchors.
- [x] 1.2 Sync the verified requirement into the main Responses compatibility
  spec.

## 2. Implementation

- [x] 2.1 Persist and clear the completed turn's effective model selector with
  the direct-WebSocket continuity record.
- [x] 2.2 Require an exact selector match before implicit session-anchor
  injection and prefix trimming.
- [x] 2.3 Preserve existing explicit client previous-response ownership rules.

## 3. Regression Coverage

- [x] 3.1 Cover same-selector anchor injection and mismatched-selector full
  replay preservation at request preparation.
- [x] 3.2 Cover a native-to-source transition on one affinity-enabled WebSocket,
  proving the source fallback occurs before a second subscription upstream
  send.

## 4. Verification

- [x] 4.1 Run focused tests, Ruff, ty, strict OpenSpec validation, and inspect
  the final diff and worktree status.
