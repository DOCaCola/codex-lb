## Why
Completed thinking currently hard-pins translated conversations to historical accounts and models, preventing safe recovery despite portable visible history.

## What Changes
- Separate envelope authentication from route compatibility.
- Prefer historical accounts for completed thinking, enforcing ownership only for active reasoning and server search.
- Omit incompatible completed thinking during explicit outbound projection without modifying stored history.

## Capabilities
### Modified Capabilities
- `claude-accounts`: translated reasoning recovery across eligible account/model changes.

## Impact
Claude Responses preparation, authenticated state decoding, regression tests. No migration or deployment configuration change. Reactive upstream 429 rotation remains a separate dispatch feature.
