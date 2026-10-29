## ADDED Requirements

### Requirement: Antigravity account enrollment
Operators SHALL enroll Antigravity accounts by Google browser sign-in or by importing a credential file. Browser sign-in MUST use PKCE (S256), offline access with consent, the native CLI client and scope set, and the remote paste redirect. Import SHALL accept the agy credential export, OmniRoute and CLIProxyAPI shapes. Enrollment MUST verify a refreshable grant, resolve the Google subject and email, and discover or onboard the Cloud Code project before an account is stored. New accounts MUST be created paused. Credentials MUST be encrypted at rest and never returned by dashboard responses.

#### Scenario: Browser enrollment
- **WHEN** an operator starts sign-in, approves in the browser and pastes the returned code
- **THEN** the account is created paused with its email, project, tier and a persisted per-account session ID

#### Scenario: Non-refreshable import
- **WHEN** an imported file has no refresh token or the token cannot be refreshed
- **THEN** no account is created and the error names the refresh failure

#### Scenario: Duplicate subject
- **WHEN** an operator enrolls a Google subject that is already enrolled
- **THEN** enrollment is rejected without changing the existing account

### Requirement: Antigravity reconnect by subject
Reconnect SHALL replace credentials only when the new grant authenticates the same Google subject. A tier, project or credit change for that subject MUST update the stored values in place. The per-account session ID, routing policy and selections SHALL survive reconnect. Reconnect with a different subject MUST be rejected without modifying the account.

#### Scenario: Subscription upgrade
- **WHEN** a Pro account reconnects after upgrading to Ultra
- **THEN** the same account updates its tier and keeps its session ID

### Requirement: Native Antigravity client identity
Every Cloud Code request SHALL send exactly the native CLI header set: `User-Agent: antigravity/cli/<version> (aidev_client; os_type=<os>; arch=<arch>; cl=<changelist>; auth_method=consumer)`, bearer authorization, JSON content type and gzip accept-encoding. The version and changelist MUST come from one verified identity record; a version MUST NOT be sent with another build's changelist or without a changelist. The platform profile SHALL be one persisted deployment setting. Each upstream request SHALL use one identity snapshot.

#### Scenario: Seeded identity
- **WHEN** no version check has succeeded yet
- **THEN** requests use the seeded verified CLI 1.4.10 record with changelist 1009308193

### Requirement: Antigravity version following
The system SHALL check the CLI update manifest for the configured platform at startup and every 24 hours. When the manifest archive URL or SHA-512 changes, it MUST download the archive, verify its SHA-512, extract the `changelist <n> with baseline` stamp from the binary and atomically persist version, changelist, build ID, SHA-512, platform and observation time. Any failure MUST keep the last verified record and surface the error. Operators SHALL be able to pin a verified version.

#### Scenario: Checksum mismatch
- **WHEN** the downloaded archive does not match the manifest SHA-512
- **THEN** the previous identity stays active and the dashboard shows the verification error

#### Scenario: Rebuilt version
- **WHEN** the manifest keeps the version string but changes its archive URL and SHA-512
- **THEN** the changelist is re-extracted before the new record is used

### Requirement: Antigravity catalog and effort families
The system SHALL discover each account's models through `fetchAvailableModels` on enrollment, periodically and on manual refresh, retaining the last successful snapshot on failure. Wire models with `-low`, `-medium` or `-high` suffixes SHALL be exposed as one client model per family (`antigravity/<family>`), and Codex reasoning effort SHALL select the matching tier, mapping unsupported efforts to the nearest advertised tier. Context and output limits SHALL be seeded from the catalog. Routing MUST only select accounts whose catalog lists the requested family.

#### Scenario: Effort selection
- **WHEN** a client requests `antigravity/gemini-3.8-flash` with effort `xhigh`
- **THEN** the upstream request uses `gemini-3.8-flash-high`

#### Scenario: Entitlement differs per account
- **WHEN** only one of two enabled accounts lists Gemini 4 Argon
- **THEN** Argon requests route only to that account

### Requirement: Antigravity quota windows
The system SHALL read `retrieveUserQuotaSummary` on refresh and after quota errors, classifying each bucket's family from its own identifier before its group (Argon, Gemini, then Claude/GPT) and its window from the explicit window field before identifiers. Used percent SHALL be `1 − remainingFraction`. A family MUST be ineligible while either of its windows is exhausted or a quota cooldown is active. Unknown quota MUST NOT be treated as exhausted. Per-model `quotaInfo` SHALL be display-only. Plan pace weights SHALL be Pro 1, Ultra 5x 5 and Ultra 20x 20; accounts SHALL display only the windows the summary reports.

#### Scenario: Weekly exhausted
- **WHEN** a Gemini family has 5-hour headroom but its weekly bucket reports 0 remaining
- **THEN** Gemini requests skip the account until the weekly reset while Claude-family requests may still use it

### Requirement: Antigravity routing and stickiness
Antigravity pools SHALL contain only Antigravity accounts. Eligibility MUST require an enabled account in ready credential state without ban, reauth or misconfiguration hold, a catalog entry for the requested family, and no exhausted window or cooldown for its quota family. Selection SHALL use the shared routing strategy with the family's binding window. A conversation SHALL stay on its account unless that account becomes ineligible.

#### Scenario: Sticky conversation
- **WHEN** a conversation's previous turn used an eligible account
- **THEN** the next turn uses the same account even if another account ranks higher

### Requirement: Antigravity Responses adaptation
Responses requests SHALL be sent to `v1internal:streamGenerateContent?alt=sse` with the native envelope: project, `agent/<cascade>/<unix_ms>/<trajectory>/<step>` request ID, `userAgent: antigravity`, `requestType: agent`, the per-account session ID and labels derived from the conversation. The `used_claude` labels SHALL report whether the account has previously dispatched an Anthropic-wire model, and `used_non_gemini_model` SHALL be `true`, as the native CLI reports them. Instructions SHALL become `systemInstruction`; messages, tool calls, tool outputs and images SHALL map to Gemini contents with exactly one adjacent function response per function call, paired by call ID. Tool schemas SHALL be compiled to the Gemini OpenAPI dialect without changing argument literals; invalid tool names SHALL be encoded reversibly. Freeform tools SHALL round-trip raw input exactly and emit custom tool events. `tool_choice` none, auto, required and specific function SHALL keep their semantics.

#### Scenario: Freeform patch
- **WHEN** the model calls the freeform `apply_patch` tool
- **THEN** the client receives a custom tool call whose input equals the generated text byte for byte

#### Scenario: Parallel calls with reversed outputs
- **WHEN** history contains two calls followed by their outputs in reverse order
- **THEN** Gemini receives each function response matched to its call ID

### Requirement: Antigravity thought signatures
Thought parts SHALL be returned to clients as reasoning summaries plus an encrypted reasoning item binding the signature to account, project, model family and client scope. On replay, a signature SHALL be attached to the first function call of its turn only when its binding matches the dispatching account and family; otherwise Gemini requests SHALL use the skip-validator sentinel and Claude-family requests SHALL omit thought parts. Foreign reasoning (OpenAI encrypted reasoning, Claude signed thinking) MUST NOT be sent as thought parts. An upstream invalid-signature rejection SHALL be retried at most once with sentinel replay before output.

#### Scenario: Account change
- **WHEN** a conversation moves to another Antigravity account
- **THEN** prior signatures are not replayed and the request uses the sentinel

### Requirement: Antigravity response projection
Gemini SSE events SHALL be unwrapped and projected into Responses events: thought text to reasoning summaries, text to output text and function calls to function or custom tool calls with stable IDs. Usage SHALL map prompt, cached, candidate and thought token counts to input, cached input, output and reasoning tokens. `STOP` SHALL complete, `MAX_TOKENS` SHALL be incomplete with `max_output_tokens`, safety finish reasons SHALL be incomplete with `content_filter`, and malformed or unexpected tool calls SHALL fail without exposing an executable call. A completion without visible text or tool call SHALL be retried once on the same account before output, then fail explicitly.

#### Scenario: Empty completion
- **WHEN** Gemini stops with only thought parts twice
- **THEN** the client receives an explicit empty-completion error after one retry

### Requirement: Antigravity error handling and failover
Upstream errors SHALL be classified from `google.rpc` ErrorInfo and RetryInfo before message text. Quota exhaustion and retry delays of at least five minutes SHALL cool the account's quota family until the reported reset and fail over. Short rate limits under three seconds SHALL retry once on the same account; longer ones SHALL cool down the account for the model and fail over. Unexplained 429s without details SHALL retry at most once on the same account and MUST NOT mark quota. 503 overloads and pre-output 500, 502 and 504 SHALL be retried at most once. A 401 SHALL refresh once and retry once. Terms-of-service bans SHALL become a durable account state without retry. A verification-required response SHALL cool the account down for 15 minutes, keep its verification notice on the account and fail over; it MUST NOT disable the account. Location, schema and other request errors MUST NOT fail over. No retry SHALL occur after output has been delivered.

#### Scenario: Quota failover
- **WHEN** the selected account returns QUOTA_EXHAUSTED and another eligible account exists
- **THEN** the request is served by the other account and the first account's family is cooled until its reset

#### Scenario: Ban
- **WHEN** an account returns a terms-of-service 403
- **THEN** the account is marked banned, never retried, and the request fails over

### Requirement: Antigravity dashboard
The add-account chooser SHALL offer Antigravity sign-in and import under an Antigravity group. Account lists and detail pages SHALL show plan, project, credential and hold state, credits, per-family 5-hour and weekly bars for reported windows, catalog selection, routing policy and trends using the shared account layout. The dashboard quota toggle SHALL include Antigravity with plan-weighted pace.

#### Scenario: Free account
- **WHEN** a free account reports only weekly buckets
- **THEN** only weekly bars are shown for its families
