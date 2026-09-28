## ADDED Requirements

### Requirement: Reactive Claude quota failover
The gateway SHALL classify upstream 429 refusals before health mutation. Fast-mode credit entitlement refusals SHALL NOT cool the pool. Unified quota rejection SHALL cool the account; ordinary model limits SHALL cool only that model. Valid Retry-After SHALL take priority over rejected-window reset headers, then a 60-second default. Deadlines SHALL persist and never shorten on concurrent writes. The gateway MAY select another authorized eligible account before output, excluding failed accounts, and MUST rebuild identity, credentials and history projection for that target. Active reasoning and server-resource ownership MUST remain enforced. A logical request SHALL permit at most four physical sends including signature recovery. Canceled requests and errors after stream ownership SHALL NOT trigger account failover. Every failed attempt SHALL settle and release admission before another attempt; exhausted recovery SHALL preserve the last upstream refusal.

#### Scenario: Alternate succeeds
- **WHEN** account A returns a retryable 429 and account B is eligible
- **THEN** B receives a freshly prepared request after A settles

#### Scenario: Entitlement refusal
- **WHEN** upstream refuses fast mode for missing credits
- **THEN** the refusal is returned without cooling ordinary account traffic

#### Scenario: Bounded recovery
- **WHEN** all selected accounts refuse or signature recovery consumes the send budget
- **THEN** no more than four physical sends occur

#### Scenario: Owned history
- **WHEN** active reasoning or server resources prevent account migration
- **THEN** the original refusal is returned without sending to another owner
