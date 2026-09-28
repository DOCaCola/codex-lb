## ADDED Requirements

### Requirement: Manual Claude reset grants
The dashboard SHALL discover cedar_ember grants for a specific authenticated Claude account and distinguish unavailable or malformed data from zero grants. Redemption SHALL require dashboard write authorization, explicit confirmation, a selected grant and operation UUID. New spends SHALL verify fresh eligibility, usability, remaining count, validity period and at-limit requirements. The organization SHALL derive from the credential's verified identity. No automatic spending or account failover SHALL occur.

Operation intent SHALL persist before POST. Concurrent attempts SHALL be serialized without holding database locks during network I/O. Identity mismatches SHALL be refused. Terminal results SHALL replay without another POST; unknown outcomes SHALL retain the operation ID and remain visible after reload/restart. Explicit same-ID retries SHALL be bounded to ten minutes from intent and respect an execution lease. New operations after expired uncertainty SHALL require a separate explicit risk acknowledgement and fresh grant eligibility. Cancellation, timeout, malformed answers and settlement-write failure MUST NOT be reported as proof that nothing was spent.

Confirmed reset results and cleared windows SHALL persist atomically with local reconciliation. Only attributable pre-reset quota restrictions for returned cleared windows SHALL be invalidated. Unknown legacy restrictions, entitlements, auth failures, uncleared windows and newer observations SHALL survive. Late pre-reset observations MUST NOT restore cleared evidence. Cleared quota SHALL become unknown until refreshed rather than fabricated zero. A refresh failure after confirmed redemption SHALL remain distinct from a failed redemption.

#### Scenario: Confirmed manual reset
- **WHEN** an authorized operator confirms a usable grant
- **THEN** one durable operation owns the claim and the dashboard shows the settled result and refreshed quota status

#### Scenario: Unknown claim outcome
- **WHEN** the claim times out after intent is persisted
- **THEN** the dashboard retains an uncertain operation and offers only bounded same-ID retry until the retry window expires

#### Scenario: Selective reset
- **WHEN** a reset clears five_hour but not seven_day
- **THEN** older five-hour evidence is invalidated while weekly, unrelated and newer restrictions remain effective
