# Proposal

## Why

Claude subscription accounts need a provider-owned authentication, routing and protocol path, rather than pretending to be OpenAI accounts or relying on another gateway. Current third-party failures make refresh ownership, native request fidelity and explicit terminal semantics essential.

## What Changes

- Add encrypted Claude accounts with PKCE login and explicit Claude Code credential-file import.
- Add model-aware pooling, durable refresh coordination, selected catalog models and truthful quota monitoring.
- Forward native Messages/count-tokens and adapt Codex Responses HTTP/WebSocket traffic to Messages, including durable continuation and compaction.
- Synchronize the advertised Claude Code version at startup and every 24 hours with manual pin/rollback.
- Integrate accounts, pause/resume, model selection and monitoring into existing dashboard surfaces.
- Verify locally with isolated upstream stubs; keep live OAuth acceptance and subscription billing qualification separate and explicitly unverified.

## Capabilities

### New Capabilities

- `claude-accounts`: Claude credentials, monitoring, version identity, pooled routing and protocol adaptation.

### Modified Capabilities

None. Existing provider-independent access, admission, settlement and transport contracts remain binding.

## Impact

Database extension and migration, provider services, model-source dispatch, Messages endpoints, Responses adaptation and account/dashboard UI. No production changes or additional proxy dependency. Existing Codex and OpenRouter behavior must remain unchanged.
