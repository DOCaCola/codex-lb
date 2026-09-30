## ADDED Requirements

### Requirement: Per-model reasoning eligibility
Each account SHALL default to all supported reasoning efforts. Operators SHALL be able to restrict individual conversation models to a nonempty set of efforts. Requests without an explicit effort SHALL use the model's advertised default for eligibility. Restrictions MUST apply before routing priority and affinity and during reused HTTP/WebSocket transports, without rewriting requests or transferring strict ownership. Ineligible requests MUST fail explicitly when no eligible account exists.

#### Scenario: Restricted high-priority account
- **WHEN** a burn-first account permits medium only and a high request arrives
- **THEN** it is excluded and an eligible normal account can serve the request

#### Scenario: Omitted effort
- **WHEN** a request omits effort and the advertised default is not permitted
- **THEN** that account is ineligible without changing the request

#### Scenario: Explicit none
- **WHEN** a request explicitly sets effort to none and an account permits only high
- **THEN** that account is ineligible even when the model default is high

#### Scenario: Unknown default
- **WHEN** a request omits effort, the model has no known advertised default, and an account has an explicit reasoning restriction
- **THEN** that account is ineligible rather than guessing an effort

#### Scenario: Unrestricted future effort
- **WHEN** an account has no reasoning restriction and an upstream model gains a new supported effort
- **THEN** the operator policy does not reject the new effort

### Requirement: Durable unavailable model configuration
Saved model IDs and reasoning selections MUST survive missing catalog entries and temporary plan changes. Configuration SHALL show unavailable saved entries and retain their editable selections. Client discovery and routing MUST exclude unavailable entries. Returning availability MUST restore the saved policy automatically.

#### Scenario: Temporary free plan
- **WHEN** a configured subscription model becomes unavailable during a downgrade
- **THEN** it remains in configuration but not the client model list, and the same settings apply after access returns

### Requirement: Dialog-local model mode
The All models toggle SHALL appear inside conversation model dialogs, not on the account detail page. Mode, model selections and reasoning restrictions SHALL be saved together, and cancellation MUST leave persisted configuration unchanged. All mode SHALL allow per-model reasoning editing without replacing curated selections. Image model dialogs MUST NOT expose the conversation-mode toggle.

#### Scenario: Cancel mode change
- **WHEN** an operator changes All models and reasoning then cancels
- **THEN** no configuration changes are saved
