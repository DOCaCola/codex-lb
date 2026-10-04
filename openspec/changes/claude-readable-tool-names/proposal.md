## Why
Translated client tools were sent to Claude under opaque `tool_<sha256>` names. Client instructions refer to tools by their real names, so Claude occasionally called a real name (for example `write_stdin`) and the gateway rejected it as undeclared (5 production failures in about 11.5k Claude requests, September 29 to October 4, 2026). Anthropic additionally fingerprints third-party harnesses on the OAuth Messages API by recognizable snake_case tool names (OmniRoute PR #2943), so plain client names are not a safe replacement.

## What Changes
- Send translated client tools under Claude Code-shaped wire names, following OmniRoute: the Claude Code canonical name when a mapping exists, PascalCase otherwise; `mcp__` names are kept; namespaced tools are qualified as CLIProxyAPI does; collisions are numbered in declaration order; names beyond Anthropic's limit are shortened with a stable digest.
- Restore the client identity through a request-local table. History calls replay under the same wire name, and forced tool choice names the wire tool.
- Accept the client's own qualified name from Claude when it identifies exactly one tool; ambiguous and undeclared names still fail explicitly.

## Capabilities
### Modified Capabilities
- `claude-accounts`: translated tool naming and undeclared-tool handling.

## Impact
Claude Responses and chat-completion translation. No schema change or deployment configuration. Active translated conversations write their tool prefix to the prompt cache once after deployment, because declarations change name.
