## MODIFIED Requirements

### Requirement: Antigravity error handling and failover
Upstream errors SHALL be classified from `google.rpc` ErrorInfo and RetryInfo before message text. Quota exhaustion and retry delays of at least five minutes SHALL cool the account's quota family until the reported reset and fail over. Short rate limits under three seconds SHALL retry once on the same account; longer ones SHALL cool down the account for the model and fail over. A 429 without details whose message names a transient limit or asks to try again later SHALL be a rate limit. Any other 429 without details is unexplained: it MUST NOT mark quota, SHALL retry at most once on the same account and only when Cloud Code sent a `Retry-After` header, and SHALL be final to the client: it SHALL carry `x-should-retry: false` and MUST NOT carry `Retry-After`. 503 overloads and pre-output 500, 502 and 504 SHALL be retried at most once. A 401 SHALL refresh once and retry once. Terms-of-service bans SHALL become a durable account state and SHALL end the request: no other account SHALL receive it, and the client SHALL receive a 403 `antigravity_account_banned` error carrying `x-should-retry: false` and no `Retry-After`. A verification-required response SHALL cool the account down for 15 minutes, keep its verification notice on the account and fail over; it MUST NOT disable the account. Location, schema and other request errors MUST NOT fail over. No retry SHALL occur after output has been delivered.

#### Scenario: Quota failover
- **WHEN** the selected account returns QUOTA_EXHAUSTED and another eligible account exists
- **THEN** the request is served by the other account and the first account's family is cooled until its reset

#### Scenario: Ban
- **WHEN** an account returns a terms-of-service 403 and another eligible account exists
- **THEN** the account is marked banned, the request is not sent to any other account, and the client receives a 403 with `x-should-retry: false`

#### Scenario: Refused content
- **WHEN** Cloud Code answers a request with a bare 429 that carries no `Retry-After` header
- **THEN** the request is not resent, and the client receives a 429 with `x-should-retry: false` and without `Retry-After`

#### Scenario: Refused content with Retry-After
- **WHEN** Cloud Code answers a request and its same-account retry with a bare 429 that carries a `Retry-After` header
- **THEN** the retry waits for that delay, and the client receives a 429 with `x-should-retry: false` and without `Retry-After`

#### Scenario: Transient wording
- **WHEN** Cloud Code answers with a 429 without details whose message says "Too many requests"
- **THEN** it is handled as a rate limit
