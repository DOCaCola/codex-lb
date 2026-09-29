## Why
Production Claude Haiku rejected a Codex request on 2026-09-29 because tools[15] carried a root schema composition. The current adapter forwards function parameters unchanged.

## What Changes
Add a bounded Claude-specific schema/argument codec for translated tools. Preserve ordinary schemas, wrap root compositions without losing constraints, relocate local references, decode upstream calls and encode history consistently. Reject unrepresentable declarations explicitly.

## Capabilities
### New Capabilities
### Modified Capabilities
- `claude-accounts`: faithful tool schema adaptation on translated paths.

## Impact
Claude protocol and Responses projection, regression tests and docs. No account settings, migration, credential changes or native Messages wire rewriting.
