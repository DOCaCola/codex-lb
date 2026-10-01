# Design

## Context
`ClaudeOpaqueState.authenticate` compared `(client_scope, conversation_id)` exactly. `conversation_id` derives from the caller's `thread-id` header. Any holder of the API key can already choose any thread ID, so the check could not stop a same-key replay; it only rejected forks, which legitimately carry their parent's history. The rationale was never recorded: the binding dates from the initial implementation (`3bf63e1f4`, 2026-09-26), and `claude-provider-history` merely preserved it.

## Decisions
1. Authentication principal is client scope. Fernet authenticity, model and source account in the envelope keep their existing roles: active reasoning and search require the original model and account; completed thinking only prefers its account.
2. Do not trust fork metadata. Codex `forked_from_thread_id` is caller-controlled, names only the immediate parent (nested forks would need server lineage) and adds nothing beyond the API key check. CLIProxyAPI (`d33f63f8`, inspected 2026-10-01) uses it only for session affinity; we keep native `parent_session_id` as an affinity hint only.
3. Remove `conversation_id` from envelopes rather than retaining an unused field. Pydantic ignores the field in older envelopes, so they still decode without a compatibility path.
4. Native resource provenance keys drop conversation for the same reason. Upstream server-tool identifiers are unguessable upstream values; client and model scope suffice. A native Claude Code fork that replays search results then resolves the original account.
5. Unchanged: session identity, `NativeSessionOwnership`, retained continuation stores, scheduling seeds and request logs remain conversation-scoped.

## Reference evidence (2026-10-01)
OpenCodex `ef0297f`, CLIProxyAPI `d33f63f8`, Sub2API main, OmniRoute `dbe703a` and Agent LB `bb718fd`: none binds replayed Claude state to a conversation. Claude Code forks reuse signed thinking under a new session ID.

## Risks / Trade-offs
A client copying its own envelopes between threads is now accepted: same key, same model/account ownership, no confidentiality or quota change. Signature acceptance across a new upstream session is established by native Claude Code forks, not by our mocks.

## Migration Plan
No migration (zero resource-origin rows in production). Deploy through the existing upgrade script when requested.
