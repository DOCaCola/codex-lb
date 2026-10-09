## ADDED Requirements

### Requirement: Generation-aware Claude authentication recovery
Prepared attempts SHALL capture the generation with the credentials actually used. After an explicit pre-output upstream401 authentication failure, the gateway MAY recover once per account per logical request: reuse an advanced generation or force an unchanged ready generation through its durable refresh claim despite future expiry. Successful refresh SHALL persist before replay. Active or uncertain refresh intents MUST NOT be stolen. Cancellation or ambiguous refresh outcome MUST NOT cause a second token exchange. Permission403 and request-specific errors MUST NOT trigger authentication refresh. Repeated401 SHALL impose ten-minute authentication backoff only on the same ready generation without an active intent; it MUST NOT revoke a newer grant. Inference retries SHALL share the four-send budget and settle before retry. Account reselection SHALL preserve authorization and strict history ownership. Failed recovery SHALL retain the upstream authentication refusal when no eligible retry succeeds.

#### Scenario: Future expiry rejected
- **WHEN** an unexpired access token receives upstream401
- **THEN** one claimed refresh and freshly prepared same-account replay are permitted

#### Scenario: Concurrent rotation
- **WHEN** the rejected generation has already been replaced
- **THEN** recovery reuses the newer credential without another token exchange

#### Scenario: Repeated rejection
- **WHEN** the recovered account receives another401
- **THEN** the rejected generation receives bounded auth backoff and no second auth recovery in this request

#### Scenario: Uncertain exchange
- **WHEN** refresh may have consumed the rotating grant
- **THEN** the durable uncertain or active intent remains protected from replay
