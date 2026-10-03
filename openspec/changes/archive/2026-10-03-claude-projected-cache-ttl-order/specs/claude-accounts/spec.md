## ADDED Requirements

### Requirement: Projected cache TTL ordering
For non-native OAuth instruction projection, the gateway SHALL preserve a valid
caller cache TTL order on the final payload. If relocation places a short
ephemeral marker before a later 1h marker, it SHALL extend that earlier marker
to 1h without downgrading the later marker or removing cache metadata.
Messages and count_tokens SHALL use the same policy. The gateway SHALL NOT
rewrite native caller cache policy or change TTLs to repair an invalid original
order, and SHALL record TTL changes as explicit projection transformations.

#### Scenario: Relocated long-lived instructions
- **WHEN** valid system 1h and user 5m cache controls are reordered by instruction relocation
- **THEN** the earlier projected short cache control becomes 1h and later short controls remain unchanged

#### Scenario: Native cache policy
- **WHEN** native Claude Code sends cache controls
- **THEN** all cache-control metadata remains unchanged

#### Scenario: Invalid original order
- **WHEN** the caller already supplies a 1h marker after a short marker
- **THEN** projection leaves the caller's cache-control values unchanged
