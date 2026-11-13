## ADDED Requirements

### Requirement: Claude Code client recognition
The gateway SHALL treat a Messages request as native Claude Code only when its user agent is
a valid Claude Code user agent in the advertised major/minor series at or above its patch,
`x-app` is `cli` or `cli-bg`, `x-stainless-lang` is `js`, the anthropic-beta list contains
`claude-code-20250219` or `oauth-2025-04-20`, and the payload carries Claude Code identity. A
recognized request SHALL keep its user agent and `x-app`, and the gateway SHALL add the OAuth beta.

#### Scenario: API-key token mode
- **WHEN** Claude Code configured with `ANTHROPIC_AUTH_TOKEN` sends the Claude Code beta without the OAuth beta
- **THEN** the request is native and upstream receives the OAuth beta added to its own betas

#### Scenario: Background and SDK sessions
- **WHEN** a request carries `x-app: cli-bg` or a `sdk-cli` user agent with `agent-sdk/0.3.10, client-app/lab-app`
- **THEN** it is native and both headers reach upstream unchanged

### Requirement: Claude Code user-agent grammar
A valid Claude Code user agent SHALL be
`claude-cli/<major>.<minor>.<patch> (external, <entrypoint>[, <name>/<value>]*)` with entrypoint
`cli`, `sdk-cli`, `sdk-ts` or `claude-vscode`. Each trailing field SHALL have a token name and a
non-empty value without parentheses; names MUST NOT repeat case-insensitively and an `agent-sdk`
value SHALL be a three-part version. Any other user agent MUST NOT be valid.

#### Scenario: Malformed user-agent field
- **WHEN** a user agent carries a bare word, an empty value, a repeated name or a non-version `agent-sdk` value
- **THEN** the request is not native

### Requirement: Native local quota refusal headers
A native Messages refusal for a fully quota-blocked Claude pool SHALL be HTTP 429 with unified
status `rejected` and no overage status. With every reset known, it SHALL name the first account to
recover: its last-resetting window as representative claim and reset, plus that window's
`5h`, `7d` or `7d_oi` status, reset and utilization `1`. Unknown resets MUST NOT be invented.

#### Scenario: Pool blocked by the five-hour window
- **WHEN** an upstream rejection blocked the only account's 5h window and Claude Code sends another request
- **THEN** codex-lb answers 429 with representative claim `five_hour`, the 5h status `rejected` and the observed reset
- **AND** Claude Code reports its 5-hour limit with that reset

#### Scenario: Reset unknown
- **WHEN** a blocked window has no observed reset
- **THEN** the refusal carries only the rejected unified status

## MODIFIED Requirements

### Requirement: Native billing-first layout preservation
The gateway SHALL recognize a leading Claude Code billing system block as native
payload identity only when Claude Code client recognition succeeds. Recognized native
requests MUST preserve system block order and cache breakpoints without synthesizing,
relocating or stabilizing billing content.

#### Scenario: Native billing-first helper
- **WHEN** qualifying Claude CLI headers accompany a billing-first system array
- **THEN** forwarding preserves the system array and cache breakpoints
- **AND** a non-qualifying client does not gain native recognition from text alone
