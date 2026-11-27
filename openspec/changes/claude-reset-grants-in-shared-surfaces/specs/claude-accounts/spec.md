## MODIFIED Requirements

### Requirement: Manual Claude reset grants
The dashboard SHALL discover cedar_ember grants for a specific authenticated Claude account and distinguish unavailable or malformed data from zero grants. Grant availability SHALL be read with the account's usage refresh; a malformed grant block SHALL make availability unknown without failing the usage read. Claude account responses SHALL report the count of banked grants (eligible, unpaused, with resets left and inside their validity period) and the nearest expiry, or unknown when no grant data was read. The dashboard card, list row, provider list, header badge and account page SHALL offer banked grants through the same reset controls as Codex reset credits. Grants SHALL be labelled by the windows they clear: a grant clearing the weekly window is a full reset, one clearing only the Fable weekly window a Fable reset, and one clearing only the five-hour window a five-hour reset.

Manual redemption SHALL require dashboard write authorization, explicit confirmation, a selected grant and operation UUID. New spends SHALL verify fresh eligibility, usability, remaining count, validity period and at-limit requirements. The organization SHALL derive from the credential's verified identity. Automatic redemption SHALL occur only when the reset-credit auto-redeem setting and reset-credit polling are both enabled, only for the soonest-expiring banked grant of a ready, enabled and verified account within five minutes of its expiry, and only through one stable operation ID per account identity, grant and expiry. No account failover SHALL occur.

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

#### Scenario: Malformed grant data
- **WHEN** the usage answer contains a cedar_ember block that does not validate
- **THEN** the usage snapshot is stored and grant availability is unknown rather than zero

#### Scenario: Banked grants in shared surfaces
- **WHEN** a Claude account has a grant with two resets left and one paused grant
- **THEN** its response reports two grants with the nearest banked expiry, and the dashboard card, list row, provider list and header badge count them like Codex reset credits

#### Scenario: Fable reset label
- **WHEN** a grant clears five_hour and seven_day_overage_included but not seven_day
- **THEN** the dialog labels it a Fable reset

#### Scenario: Automatic redemption before expiry
- **WHEN** auto-redeem and reset-credit polling are enabled and a banked grant expires in four minutes
- **THEN** the leader spends it once under a stable operation ID, and later ticks reuse that settled operation without another POST

#### Scenario: Automatic redemption disabled
- **WHEN** the auto-redeem setting or reset-credit polling is disabled
- **THEN** no Claude grant is spent automatically
