## Why
Claude's model catalog started listing `claude-haiku-5-5` and `claude-fable-5-1` on 2026-10-10, and codex-lb offers both to clients. Every Haiku 5.5 request with instructions failed with "OAuth instruction placement is not qualified for this Claude model": instruction placement and structured output are gated on a hardcoded table of eight models, and models missing from it are refused before dispatch. Every new Claude release therefore breaks until the table is edited.

CLIProxyAPI solves the same placement decision the other way round. It keeps a list of the legacy models that reject a mid-conversation `system` turn, derived from 314 captured native Claude Code requests (the turn appears on Opus 5 and Sonnet 5, never on the 43 requests to legacy models), and treats unknown and future models optimistically. It does not gate structured output by model.

## What Changes
- Mid-conversation `system` turns become the placement for every Claude model except CLIProxyAPI's legacy list (Claude 3.5 Haiku, 3.7 Sonnet, Haiku 4.5, Opus 4 to 4.7, Sonnet 4 to 4.6), which keeps the `<system-reminder>` user-turn placement. Unlisted models are no longer refused.
- Structured output is forwarded for every model; Anthropic answers for models that lack it.
- The model policy table keeps only its reasoning fallback for catalog entries stored without capabilities.

## Capabilities
### Modified Capabilities
- `claude-accounts`: instruction placement follows a legacy-model list; unlisted models are dispatched.

## Impact
Claude capabilities, OAuth request projection and Responses translation, with unit tests. No schema or client-visible change besides newly working models.
