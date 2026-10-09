## REMOVED Requirements

### Requirement: Telemetry payload field allowlist
**Reason**: The fork does not send telemetry; there is no payload.
**Migration**: None.

### Requirement: Consent state and default activation
**Reason**: No telemetry, so no consent state. The consent columns are dropped.
**Migration**: None; the stored decision is deleted by the migration.

### Requirement: One-time consent dialog with exact payload preview
**Reason**: The first-visit consent dialog is removed with the feature.
**Migration**: None.

### Requirement: Settings toggle and environment kill switch
**Reason**: Nothing to toggle. `CODEX_LB_TELEMETRY_ENABLED` is a removed setting.
**Migration**: Unset the variable; startup warns while it is still set.

### Requirement: Startup notice while undecided
**Reason**: No consent state exists.
**Migration**: None.

### Requirement: Disabled means zero telemetry traffic
**Reason**: Zero telemetry traffic is now unconditional: the sender is deleted.
**Migration**: None.

### Requirement: Client family allowlist mapping
**Reason**: Only used to build the snapshot.
**Migration**: None.

### Requirement: Model catalog allowlist with per-model reasoning mix
**Reason**: Only used to build the snapshot.
**Migration**: None.

### Requirement: Fail-honest request-family attribution
**Reason**: Only used to build the snapshot.
**Migration**: None.

### Requirement: Random instance identity
**Reason**: The instance identity and its encrypted signing key are dropped.
**Migration**: None.

### Requirement: Transmission cadence and failure isolation
**Reason**: The scheduler is deleted. `CODEX_LB_TELEMETRY_ENDPOINT` is a removed setting.
**Migration**: Unset the variable; startup warns while it is still set.

### Requirement: Bucketed sensitive aggregates
**Reason**: Only used to build the snapshot.
**Migration**: None.

### Requirement: Snapshot payload declares active consent
**Reason**: No snapshot is sent.
**Migration**: None.

### Requirement: Dashboard opt-out notification
**Reason**: Nothing to opt out of.
**Migration**: None.
