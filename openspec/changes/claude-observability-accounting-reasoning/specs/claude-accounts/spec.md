## MODIFIED Requirements

### Requirement: Claude request usage and timing
Claude native and adapted request logs SHALL preserve inclusive input/output tokens, separately reported cache reads and writes, and only provider-reported reasoning tokens. The gateway SHALL measure upstream-attempt duration and time to first nonempty generated text, thinking or tool payload from a monotonic pre-open anchor. Metadata, pings and empty deltas MUST NOT establish first-token latency. Error, cancellation and truncated streams SHALL finalize duration without inventing first-token latency.

#### Scenario: Cached thinking stream
- **WHEN** a stream reports uncached input, cache reads, cache writes and output but no reasoning token count
- **THEN** its inclusive totals and cache breakdown persist, while reasoning tokens remain unknown

### Requirement: Claude reasoning policies
Known budget-thinking models SHALL advertise reasoning separately from adaptive-thinking models. Requested efforts SHALL map to a documented budget below the effective output cap, and impossible explicit caps SHALL fail before upstream dispatch. Translated requests SHALL reject unsupported sampling controls when thinking is enabled before dispatch. Omitted/off reasoning SHALL not enable thinking. Request logs SHALL distinguish requested effort from effective upstream effort, thinking mode and budget when applicable across native Messages and translated Responses, Chat and WebSocket routes, without inferring effort from a native budget. Upstream effort and thinking mode SHALL record the values sent upstream; when the upstream request leaves either to the provider's model-dependent default, it SHALL be recorded as unset rather than inferred. Explicit null sampling controls SHALL be treated as absent.

#### Scenario: Thinking left to the model default
- **WHEN** a Claude request is dispatched without a `thinking` block or `output_config.effort`
- **THEN** its request log records upstream thinking mode and upstream effort as unset, not as disabled or a guessed default

#### Scenario: Haiku reasoning cap
- **WHEN** Haiku 4.5 receives high reasoning with an explicit output cap below the mapped budget
- **THEN** the request fails before dispatch rather than enlarging the cap
