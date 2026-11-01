## MODIFIED Requirements

### Requirement: Advertised version following
The service SHALL asynchronously follow the canonical stable Claude Code release at startup when stale and every 24 hours, sharing state across workers. A newer release SHALL be adopted only after its published native build was downloaded, matched to the registry's integrity hash and scanned for its Stainless SDK and runtime versions; requests SHALL send the CLI, SDK and runtime versions of one verified build. The build MUST NOT be executed. The service MUST preserve the last verified version on discovery or verification failure, distinguish last checked from last changed, support manual pin/rollback to a verified build, and use one immutable identity snapshot per request. It MUST NOT fabricate private billing fingerprints.

#### Scenario: Unchanged version check
- **WHEN** discovery succeeds with the current version
- **THEN** last checked advances while last changed remains unchanged

#### Scenario: New release verification
- **WHEN** discovery returns a newer release
- **THEN** it is advertised only after its build yielded one SDK and one runtime version, which are sent with it
- **AND** a failed verification keeps the last verified build and retries later
