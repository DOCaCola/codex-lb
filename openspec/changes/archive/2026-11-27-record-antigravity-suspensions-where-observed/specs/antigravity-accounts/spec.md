## ADDED Requirements

### Requirement: Structured Antigravity suspension signature
A `google.rpc.ErrorInfo` reason of `TOS_VIOLATION` SHALL classify as a terms-of-service ban regardless of HTTP status and message wording, including an error frame inside an HTTP 200 stream.

#### Scenario: Structured suspension with other wording
- **WHEN** Cloud Code returns a 403 whose ErrorInfo reason is `TOS_VIOLATION` and whose message is not the known sentence
- **THEN** the account is marked banned and the request ends with `antigravity_account_banned`

### Requirement: Antigravity rejections are recorded where observed
What a classified rejection proves about its account SHALL be recorded when the rejection is observed: on the HTTP response, on the first event, mid-stream after output reached the client, and on a later round of the same response. Recording MUST NOT depend on whether the request is retried. A rejection of the gateway's web search call SHALL record account-level holds and MUST NOT cool the conversation's quota family or model.

#### Scenario: Suspension after output
- **WHEN** a response has delivered visible output and the stream then carries a `TOS_VIOLATION` error frame
- **THEN** the account is marked banned, no other account receives the request, and the client receives the ban error

#### Scenario: Suspension seen by web search
- **WHEN** the gateway's search call on the account is rejected with `TOS_VIOLATION`
- **THEN** the account is marked banned and the model receives the search tool error
