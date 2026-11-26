## ADDED Requirements

### Requirement: OpenAI API accounts
Operators SHALL create, rename, pause, resume, replace the key of and delete OpenAI API accounts using a Platform
project API key. The key MUST be validated with `GET /v1/models` before the account is created, MUST be encrypted at
rest, and MUST be absent from dashboard responses.

#### Scenario: Valid key
- **WHEN** an operator submits a key that `GET /v1/models` accepts
- **THEN** the account is created with its synchronized catalog and no models enabled

#### Scenario: Rejected key
- **WHEN** `GET /v1/models` rejects the key
- **THEN** no account is created and the dashboard shows the provider's status without the key

### Requirement: API-key models are published separately
Selected models SHALL be published as `openai-apikey/<model>` and forwarded upstream with the bare model id. Text
models SHALL exclude embedding, audio, speech, transcription, moderation, realtime, legacy completion and video
families; image models SHALL be `gpt-image-*` and `chatgpt-image-*`. New catalog models MUST stay disabled
until selected. A model removed upstream MUST stay listed as unavailable and MUST NOT be served by another provider.

#### Scenario: Forwarded model id
- **WHEN** a client requests `openai-apikey/gpt-6.2-astra` on `/v1/responses`
- **THEN** the upstream request names `gpt-6.2-astra`

#### Scenario: Image model on a text route
- **WHEN** a client requests an API-key image model on `/v1/responses`
- **THEN** the response is 400 directing the client to `/v1/images`

### Requirement: Codex routes exclude API-key models
The Codex model list MUST NOT include `openai_apikey` models, and Codex backend Responses and compact requests for
them MUST fail with 400 stating that OpenAI API models are served on `/v1` only. `/v1/models`,
`/v1/responses`, `/v1/chat/completions` and `/v1/messages` SHALL serve them.

#### Scenario: Codex model list
- **WHEN** a Codex client fetches its model list with an API-key model enabled
- **THEN** the model is absent

### Requirement: Continuations are local
Responses requests for API-key models SHALL be sent with `store: false` and continue conversations from
codex-lb's own history, like the other stateless providers, so that any eligible account in the pool can serve the
next turn. A continuation MUST NOT depend on a response stored in an OpenAI organization.

#### Scenario: Continuation after failover
- **WHEN** a client continues by `previous_response_id` after the account that served the previous turn is cooling
  down
- **THEN** another eligible account serves the turn with the replayed history

### Requirement: Billing exhaustion skips the account
An upstream refusal with code `insufficient_quota`, `credit_balance_exhausted`, `credit_balance_too_low`,
`insufficient_balance`, `billing_hard_limit_reached`, `organization_spend_limit_exceeded`,
`project_spend_limit_exceeded` or `organization_usage_limit_exceeded` MUST cool the whole account until its next
configured credit renewal, or for six hours without one. A manual refresh MUST clear the account's cooldowns.

#### Scenario: Only account exhausted
- **WHEN** the only account is cooling down after a billing refusal
- **THEN** the request fails with 429 and a `Retry-After` for the remaining cooldown

### Requirement: Refusals fail over within API-key accounts
Rate-limit 429s MUST cool the requested model for the provider's `Retry-After`. Before any output is delivered,
401 and 429 refusals SHALL try another eligible API-key account for the same model. They MUST NOT fall back to
subscription accounts or another model.

#### Scenario: Credit exhausted with a second key
- **WHEN** the first account answers 429 `insufficient_quota` and a second account serves the same model
- **THEN** the second account serves the request and the first is skipped until its renewal

### Requirement: API-key image models
`/v1/images/generations`, `/v1/images/edits` and the Codex image routes SHALL serve `openai-apikey/` image
models by posting the JSON Images body with the bare model id to the account's Images endpoint. Event streams MUST
pass through, usage MUST be priced from the API price table, and the request MUST be logged against the account.

#### Scenario: Multipart edit
- **WHEN** a `/v1/images/edits` multipart request names an API-key image model
- **THEN** the uploads are sent upstream as `images[].image_url` data URLs

### Requirement: Estimated monthly credit
An account MAY store a monthly credit amount and a renewal day of month. The dashboard SHALL show the current cycle,
the cost recorded on the account since the cycle started, the estimated remainder and any active billing
exhaustion, labelled as an estimate. The renewal day MUST be clamped to the length of short months.

#### Scenario: Renewal on the 31st
- **WHEN** the renewal day is 31 and the current month has 30 days
- **THEN** the cycle renews on the 30th
