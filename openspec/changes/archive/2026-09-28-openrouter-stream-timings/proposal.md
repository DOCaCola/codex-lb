# Proposal
## Why
Successful OpenRouter streams lack TTFT and TPS because forwarding only consumes
provider-specific timing metadata. The gateway can observe streaming content.
## What Changes
- Measure OpenRouter attempt duration and first generated content locally.
- Show estimated generation TPS only for successful, sufficiently long streams.
- Leave unknown TTFT unknown and preserve other providers' timing contracts.
- Display Free/Paid key tiers without inferring commercial plans, and label compatible upstream HTTP as HTTP.
## Capabilities
### New Capabilities
None.
### Modified Capabilities
- openrouter-accounts: gateway-observed timing and truthful throughput.
## Impact
Source forwarding, request-log consumers, dashboard speed formatting and reports.
No migration, config setting, commit or deployment required by this task.
