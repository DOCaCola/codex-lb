# Proposal

## Why

An isolated real Codex app-server/Claude Code comparison found that the default Codex web-search declaration fails before Claude dispatch, and translated requests have no prompt-cache boundaries. The same comparison exposed absent synthesized session metadata and an inconsistent architecture/header profile.

## What Changes

- Translate hosted web search end to end, including search lifecycle, citations and account-bound opaque replay.
- Add deterministic caching only to translated Responses traffic, preserving native caller-owned markers.
- Synthesize coherent local device/session metadata without fabricating a provider account UUID; align reviewed headers with the runtime and captured CLI behavior.
- Retain explicit errors for unsupported search semantics, and existing pause-turn and ownership guarantees.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: translated search, caching and synthesized wire identity.

## Impact

Claude protocol/projection and dispatch modules, route/unit tests, and the isolated parity lab. No deployment, new dependency, migration, paid fallback or billing-fingerprint synthesis.
