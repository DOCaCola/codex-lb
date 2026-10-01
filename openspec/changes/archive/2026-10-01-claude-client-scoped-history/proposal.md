## Why
On 2026-10-01 a forked Codex thread (`01a0f80a…`, forked from `01a0f74e…`) switched to Opus 5.5 and failed before dispatch with `invalid_provider_history`: "Claude reasoning state belongs to another client or conversation". All 263 inherited envelopes were genuine, untampered and owned by the same API key, model and account. They were rejected only because their conversation ID differed from the child's `thread-id`.

The conversation ID is caller-supplied (`thread-id` header). Under one API key it identifies routing and retention context, not an authorization principal, so binding authentication to it blocks legitimate forks without protecting anything.

## What Changes
Authenticate Claude envelopes and native server-resource provenance against client scope (API key) plus their encrypted model/account contents. Conversation identity continues to govern session identity, routing affinity, owner records and retained continuation, but no longer authorizes history. Model and account ownership for active reasoning and server search remain strict.

## Capabilities
### New Capabilities
### Modified Capabilities
- `claude-accounts`: client-scoped history authentication and resource provenance.

## Impact
Claude opaque envelopes, translated/native/Chat replay authentication, native resource keys and their tests/specs. New envelopes stop carrying a conversation ID; existing envelopes remain decodable because the unused field is ignored. Production had zero resource-origin rows on 2026-10-01, so rekeying needs no migration. No settings, schema or credential changes.
