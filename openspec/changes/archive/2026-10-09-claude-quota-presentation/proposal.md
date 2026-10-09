## Why
Claude Pro usage successfully reports shared quotas but returns null model-specific windows. The detail view renders these as misleading unknown limits. Claude's chart also lacks the Codex weekly pacing guideline because quota history does not retain reset deadlines.

## What Changes
- Omit absent model-specific windows after a successful observation, without hiding known stale observations or inventing entitlements.
- Persist reported reset deadlines with future quota samples; leave legacy deadlines unknown.
- Share the Codex pacing formula and render a distinct dashed weekly plan on the existing chart, bounded by observed reset cycles.

## Capabilities
### Modified Capabilities
- `claude-accounts`: optional model-specific quota display.
- `provider-account-trends`: reset-aware Claude weekly pacing.

## Impact
One nullable-column migration, Claude quota presentation and shared trend contracts. No production configuration, commit or deployment in this task.
