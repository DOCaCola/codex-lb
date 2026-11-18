## ADDED Requirements

### Requirement: Antigravity system instruction rewriting
The adapter SHALL rewrite known content-filter triggers in `systemInstruction` text in plain words, without invisible characters, and SHALL log only the names of the rules that fired. No other request text SHALL be rewritten.

#### Scenario: Codex prompt
- **WHEN** a Codex request routed to Antigravity has instructions beginning "You are Codex, an agent based on GPT-6. You and the user share one workspace."
- **THEN** `systemInstruction` begins "You are a helpful coding assistant. You and the user share one workspace." and contains no zero-width or combining characters

#### Scenario: Claude Code prompt
- **WHEN** the system text contains Claude Code's identity line, its interactive-agent role sentence and its dual-use security sentence
- **THEN** the identity line is removed and the two sentences take the neutral wording verified in CLIProxyAPI #7627

#### Scenario: Identity only in user text
- **WHEN** a user message contains "You are Codex, an agent based on GPT-6."
- **THEN** the message reaches Gemini unchanged

#### Scenario: Instructions consisting only of an identity line
- **WHEN** the only system text is "You are a Claude agent, built on Anthropic's Claude Agent SDK."
- **THEN** the request carries no `systemInstruction`
