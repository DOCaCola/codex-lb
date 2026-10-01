## ADDED Requirements

### Requirement: Native billing-first layout preservation
The gateway SHALL recognize a leading Claude Code billing system block as native
payload identity only when the existing CLI software and OAuth header checks
succeed. Recognized native requests MUST preserve system block order and cache
breakpoints without synthesizing, relocating or stabilizing billing content.

#### Scenario: Native billing-first helper
- **WHEN** qualifying Claude CLI headers accompany a billing-first system array
- **THEN** forwarding preserves the system array and cache breakpoints
- **AND** a non-qualifying client does not gain native recognition from text alone
