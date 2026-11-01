## ADDED Requirements

### Requirement: Claude organization OAuth refusal
An upstream 403 `permission_error` whose whole message is "OAuth authentication is currently not allowed for this organization" SHALL block the Claude account for routing when it was sent with the account's current credential generation. The request SHALL fail over to another eligible account within its send budget. A blocked account MUST NOT be selected, including through sticky or session affinity. When only blocked accounts remain, selection SHALL fail locally with 400 `claude_subscription_inactive` without contacting Anthropic, except that the request that recorded the block reports Anthropic's refusal. A usage or subscription metadata refresh requested after the block and answered successfully, or a reconnect, SHALL clear the block. Other 403 responses, including messages that merely contain the refusal text, MUST NOT block the account.

#### Scenario: Lapsed subscription in a pool
- **WHEN** one of two eligible accounts answers with the organization OAuth refusal
- **THEN** the request completes on the other account
- **AND** later requests do not select the refused account

#### Scenario: Every account lapsed
- **WHEN** every eligible account has answered with the organization OAuth refusal
- **THEN** that request reports Anthropic's refusal
- **AND** a following request fails with 400 `claude_subscription_inactive` without an upstream send

#### Scenario: Subscription renewed
- **WHEN** a usage or subscription refresh requested after the block succeeds
- **THEN** the account is eligible again
- **AND** a refresh requested before the block leaves it blocked

#### Scenario: Replaced credential
- **WHEN** a refusal arrives for a credential generation that has since been replaced
- **THEN** the account is not blocked
