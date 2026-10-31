## MODIFIED Requirements

### Requirement: Antigravity error handling and failover
Upstream errors SHALL be classified from `google.rpc` ErrorInfo and RetryInfo before message text. Quota exhaustion and retry delays of at least five minutes SHALL cool the account's quota family until the reported reset and fail over. Short rate limits under three seconds SHALL retry once on the same account; longer ones SHALL cool down the account for the model and fail over. Unexplained 429s without details SHALL retry at most once on the same account and MUST NOT mark quota. A reported unexplained 429 SHALL be final to the client: it SHALL carry `x-should-retry: false` and MUST NOT carry `Retry-After`. 503 overloads and pre-output 500, 502 and 504 SHALL be retried at most once. A 401 SHALL refresh once and retry once. Terms-of-service bans SHALL become a durable account state without retry. A verification-required response SHALL cool the account down for 15 minutes, keep its verification notice on the account and fail over; it MUST NOT disable the account. Location, schema and other request errors MUST NOT fail over. No retry SHALL occur after output has been delivered.

#### Scenario: Quota failover
- **WHEN** the selected account returns QUOTA_EXHAUSTED and another eligible account exists
- **THEN** the request is served by the other account and the first account's family is cooled until its reset

#### Scenario: Ban
- **WHEN** an account returns a terms-of-service 403
- **THEN** the account is marked banned, never retried, and the request fails over

#### Scenario: Refused content
- **WHEN** Cloud Code answers a request and its same-account retry with a bare 429 that carries a `Retry-After` header
- **THEN** the retry waits for that delay, and the client receives a 429 with `x-should-retry: false` and without `Retry-After`
