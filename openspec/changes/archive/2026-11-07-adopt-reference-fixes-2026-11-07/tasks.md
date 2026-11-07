## 1. Implementation

- [x] 1.1 Request Claude Code's scope set in the Claude authorize URL
- [x] 1.2 Raise positive output limits below 16 at the Codex backend boundary only
- [x] 1.3 Fail OpenRouter, Claude and Antigravity syncs that discover no models

## 2. Verification

- [x] 2.1 Unit tests for the scope string, output floor (Responses, Chat, Claude Code) and empty discovery per provider
- [x] 2.2 Full unit and integration suites, ruff, ty and repository checks
