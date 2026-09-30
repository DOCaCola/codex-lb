# Proposal

## Why

Account details and model controls differ between providers, and Claude chart alignment can fragment measured quota lines when the pacing guideline adds timestamps. Operators also need real per-account model restrictions for Codex and routing priority for OpenRouter.

## What Changes

- Share account model availability controls and dialog presentation across providers; use compact usage/monitoring/action sections for Claude.
- Persist all-versus-selected mode, defaulting to all for Codex and selected for Claude/OpenRouter, retaining curated selections when switching.
- Enforce Codex model restrictions in fresh selection and reused transports without bypassing ownership or upstream capabilities.
- Add OpenRouter manual routing policy within its own eligible pool.
- Fix chart alignment without filling unknown observation hours or connecting reset cycles.

## Capabilities

### New Capabilities
- `account-model-controls`: Provider-consistent model controls and native account eligibility.

### Modified Capabilities
- `openrouter-accounts`: Explicit all-conversation-model mode and manual routing priority.
- `provider-account-trends`: Correct alignment of measured quota and weekly guidelines.
- `claude-accounts`: Opt-in dynamic conversation catalog mode.

## Impact

Account persistence/migration, dashboard APIs, provider model projection, native routing/reuse gates, and account detail/model-dialog/chart components. No client changes or deployment.
