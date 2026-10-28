# Context

Production replaced DOCa Claude at 10:30:41 UTC on 2026-10-28; the catalog refresh
completed at 10:31:10. No request arrived during that 29-second gap, but the preceding
unavailable-model change made such a request fail with a final 400. Model metadata is
account-neutral enough to keep serving selected models until rediscovery. If the new
identity lacks entitlement, Anthropic rejects that request and the scheduled refresh
removes the model. Same-identity subscription changes already behave this way.

Replacement races use `claude_identity_changed` (503, Retry-After 1): retrying prepares
against the current identity. Resources issued to the previous identity cannot be
retried successfully, so native threads keep `thread_not_found` to request full history.
Tests simulate replacement during credential preparation without upstream traffic.
