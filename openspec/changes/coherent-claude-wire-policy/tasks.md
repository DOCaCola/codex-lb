## Implementation
- [x] Centralize session projection, helper classification and beta decisions.
- [x] Preserve native hints and implement endpoint header defaults.
- [x] Cover native/translated routes, identity isolation and malformed inputs.
- [x] Run checks and synchronize the capability specification.

## Verification

- 134 Claude unit/integration tests passed, including Messages helper and count-token route captures.
- Ruff and Claude-module type checking passed; git diff whitespace check passed.
- Strict change validation and all 70 capability specifications passed.
- Tests exercise mock/loopback transports; no successful live OAuth/billing qualification.
- Archival and deployment remain separate operator actions.
