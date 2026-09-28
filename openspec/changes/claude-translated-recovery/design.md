## Context
OpenCodex separates route identity from reasoning replay. Our authenticated envelopes already retain durable provenance, so no process-local identity cache is needed.

## Decisions
Authenticate client/conversation scope independently of model compatibility. A reasoning block is completed only after a subsequent explicit user message; tool outputs do not end a turn. Active reasoning and all server search remain model/account-bound. Completed thinking supplies a soft preference and is omitted on a different selected account/model. Keep logical input immutable and log omission counts only. Preserve strict decode for existing exact-target consumers by sharing authentication.

## Non-goals
Automatic mid-request 429 account rotation, portable server resources, cross-provider opaque conversion, production deployment.

## Risks
Conservative active-turn classification may refuse migrations that upstream could accept; this is preferable to modifying active tool reasoning without live evidence. Authentication failures must never become omission.
