## ADDED Requirements

### Requirement: Claude reports the cause of cache misses

Translated Claude Messages requests SHALL carry `diagnostics` with
`previous_message_id` set to the most recent completed message of the same
conversation on the same account, or `null` when none is known, together with
the `cache-diagnosis-2026-04-07` beta. A message SHALL become the reference only
after its response stops with a stop reason, SHALL expire after one hour, and
SHALL NOT be replaced by a message from a request sent earlier. Native requests
SHALL be forwarded with the diagnostics their client sends. When a response
reports `diagnostics.cache_miss_reason` on `message_start`, `message_delta` or a
non-streamed message, the service SHALL log its type and missed input tokens
with the conversation and account. The `diagnostics` field SHALL NOT count as a
changed parameter in cache-miss attribution.

#### Scenario: Second translated turn

- **GIVEN** a translated turn on account A completed with message `msg_first`
- **WHEN** the same conversation sends its next turn on account A
- **THEN** the request carries `diagnostics.previous_message_id` `msg_first` and the cache-diagnosis beta

#### Scenario: Account changes

- **GIVEN** the reference was recorded on account A
- **WHEN** the conversation's next turn is sent on account B
- **THEN** `previous_message_id` is `null`

#### Scenario: Unfinished turn

- **GIVEN** a translated turn whose stream ended before its stop reason
- **WHEN** the conversation sends its next turn
- **THEN** the unfinished message is not the reference

#### Scenario: Anthropic explains a miss

- **WHEN** a response reports `cache_miss_reason` of type `tools_changed` with 1234 missed tokens
- **THEN** the service logs `claude_cache_diagnosis` with that type, the token count, the conversation and the account
