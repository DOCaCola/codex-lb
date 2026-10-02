## ADDED Requirements

### Requirement: Accounts carry a credit policy
Each account SHALL have a credit policy of `spend` or `never`, defaulting to `spend`. Under `spend`, credit-backed capacity overrides quota exhaustion as before. Under `never`, credit metadata MUST NOT override quota exhaustion: effective status MUST be derived from usage, an exhausted primary window MUST yield `rate_limited` and an exhausted long window MUST yield `quota_exceeded`, and the account MUST NOT be selected for routing. The usage updater MUST persist that blocked status and MUST restore the account to `active` once usage shows available quota. Pooled credit headers and rate-limit payloads MUST exclude accounts under `never`. Paused and deactivated accounts keep their status regardless of policy. The policy SHALL be changeable through `PUT /api/accounts/{id}/credit-policy`, and the change MUST take effect for new selections on every replica.

#### Scenario: Credits do not keep a never account routable
- **GIVEN** an account with credit policy `never`
- **AND** its weekly window reports 100% usage while its usage snapshot reports a positive credit balance
- **WHEN** selection or the usage updater derives its status
- **THEN** the account is `quota_exceeded` and not selectable

#### Scenario: Spend keeps the credit override
- **GIVEN** the same usage on an account with credit policy `spend`
- **WHEN** its status is derived
- **THEN** the account remains `active`

#### Scenario: Recovery after reset
- **GIVEN** a `never` account blocked by an exhausted window
- **WHEN** refreshed usage shows available quota
- **THEN** the usage updater restores it to `active` and routing resumes

#### Scenario: Pooled credits omit never accounts
- **WHEN** rate-limit headers or payloads aggregate pooled credits
- **THEN** credits of `never` accounts are not included

#### Scenario: Policy change reaches peer replicas
- **GIVEN** an exhausted account with credits under `spend`
- **WHEN** an operator sets its policy to `never` on one replica
- **THEN** every replica stops selecting the account
