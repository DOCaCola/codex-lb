## ADDED Requirements

### Requirement: Claude sign-in requests the Claude Code scope set
The Claude authorize URL SHALL request exactly the scopes Claude Code requests:
`org:create_api_key user:profile user:inference user:sessions:claude_code
user:mcp_servers user:file_upload`. Token refresh SHALL NOT send a scope.

#### Scenario: Operator starts Claude sign-in
- **WHEN** an operator starts browser sign-in or reauthorization for a Claude account
- **THEN** the authorize URL carries that scope set, including `org:create_api_key`
