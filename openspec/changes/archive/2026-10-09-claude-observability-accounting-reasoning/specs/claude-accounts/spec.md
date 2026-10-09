## MODIFIED Requirements

### Requirement: Claude request usage and timing
Claude native and adapted request logs SHALL preserve inclusive input/output tokens, separately reported cache reads and writes, and only provider-reported reasoning tokens. The gateway SHALL measure upstream-attempt duration and time to first nonempty generated text, thinking or tool payload from a monotonic pre-open anchor. Nonempty redacted-thinking data and thinking signatures SHALL establish opaque first output. Metadata, pings and empty deltas MUST NOT establish first-token latency. Error, cancellation and truncated streams SHALL finalize duration without inventing first-token latency. Timing observation MUST precede Responses adaptation and MUST NOT expose opaque contents or infer reasoning token counts.

#### Scenario: Cached thinking stream
- **WHEN** a stream reports uncached input, cache reads, cache writes and output but no reasoning token count
- **THEN** its inclusive totals and cache breakdown persist, while reasoning tokens remain unknown

#### Scenario: Opaque first output
- **WHEN** a native stream emits nonempty redacted-thinking data or a thinking signature before visible output
- **THEN** TTFT anchors to that opaque upstream output and completion retains the same monotonic attempt anchor
- **AND** empty opaque fields, pings and terminal events alone do not establish TTFT

### Requirement: Claude reasoning policies
Known budget-thinking models SHALL advertise reasoning separately from adaptive-thinking models. Requested efforts SHALL map to a documented budget below the effective output cap, and impossible explicit caps SHALL fail before upstream dispatch. Translated requests SHALL reject unsupported sampling controls when thinking is enabled before dispatch. Omitted/off reasoning SHALL not enable thinking. Request logs SHALL distinguish requested effort from effective upstream effort, thinking mode and budget when applicable across native Messages and translated Responses, Chat and WebSocket routes, without inferring effort from a native budget. Upstream effort and thinking mode SHALL record the values sent upstream; when the upstream request leaves either to the provider's model-dependent default, it SHALL be recorded as unset rather than inferred. Explicit null sampling controls SHALL be treated as absent.

#### Scenario: Thinking left to the model default
- **WHEN** a Claude request is dispatched without a `thinking` block or `output_config.effort`
- **THEN** its request log records upstream thinking mode and upstream effort as unset, not as disabled or a guessed default

#### Scenario: Haiku reasoning cap
- **WHEN** Haiku 4.5 receives high reasoning with an explicit output cap below the mapped budget
- **THEN** the request fails before dispatch rather than enlarging the cap

## ADDED Requirements

### Requirement: Claude reasoning levels from catalog capabilities
When Claude's model catalog reports a model's capabilities, advertised reasoning levels and the thinking mode SHALL be derived from them: adaptive-thinking models SHALL advertise exactly the reported effort levels, including `xhigh` where reported; budget-only models SHALL advertise the documented budget ladder; a model reporting neither SHALL advertise no reasoning. The explicit policy table SHALL apply only when stored catalog entries lack capabilities. The advertised default SHALL be the provider's API default effort for adaptive models (`medium` for Claude Opus 5.5, otherwise `high`) and `medium` for budget models. A requested `xhigh` or `max` the model does not support SHALL be sent as `high`; a requested effort SHALL never be sent as a higher level.

#### Scenario: Opus 5.5 advertises xhigh from the catalog
- **WHEN** the catalog reports adaptive thinking with low, medium, high, xhigh and max effort for Claude Opus 5.5
- **THEN** the Codex model catalog advertises those five levels with default `medium`, and a request for `xhigh` is sent upstream as `xhigh`

#### Scenario: Unsupported xhigh steps down
- **WHEN** a client requests `xhigh` for a model whose catalog reports effort up to `max` without `xhigh`
- **THEN** the request is sent with effort `high`, not `max`
