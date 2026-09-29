# Share routing policy with Claude

## Why
Claude filters exhausted quotas but ignores the dashboard routing strategy.
Reuse the shared policy with normalized Claude data, not OpenAI plan estimates.

## What Changes
- Apply shared strategy/reset/relative-availability settings to Claude selection.
- Normalize healthy fresh Claude quota windows with equal account capacities.
- Preserve authorized hard owners and eligible soft affinity.
- Add a provider-specific Claude single-account target and admission timestamps.

## Capabilities
### Modified Capabilities
- claude-accounts: shared routing policy.

## Impact
Claude routing, dashboard settings and routing UI, SQL migration and tests.
