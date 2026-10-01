## MODIFIED Requirements

### Requirement: Dashboard request logs show generation speed

The dashboard request-log table MUST show time to first token and output-token generation speed when the required latency and output-token fields are available. Native and generic source generation speed MUST use non-reasoning output tokens divided by elapsed generation time after time to first token, not total input plus output tokens and not total request latency including TTFT. When reasoning-token usage is unknown, it MUST be treated as zero for that native/generic metric. Claude and OpenRouter MUST instead use total reported output, mark TPS estimated and require successful status, nonnegative known TTFT and at least one second of post-TTFT observation. The displayed metric MUST remain named `TPS`.

#### Scenario: TPS excludes TTFT, input tokens, and reasoning tokens

- **GIVEN** a successful native request log has 1,000 input tokens, 200 output tokens, including 40 reasoning tokens, 1,000 ms total latency, and 200 ms TTFT
- **WHEN** the dashboard renders request logs
- **THEN** it shows TTFT as 200ms
- **AND** it shows TPS as `(200 - 40) / 0.8 = 200.0`

#### Scenario: Unknown reasoning usage is treated as zero

- **GIVEN** a native or generic source request has output tokens, valid total latency and TTFT, but no reasoning-token usage
- **WHEN** the dashboard calculates TPS
- **THEN** it uses the full output-token count as non-reasoning output

#### Scenario: missing speed inputs stay blank

- **GIVEN** a request log is missing TTFT, total latency, or output tokens
- **WHEN** the dashboard renders request logs
- **THEN** it does not show a misleading calculated TPS value

#### Scenario: invalid speed inputs stay blank

- **GIVEN** a request log has output tokens and latency fields
- **AND** either total latency is less than or equal to TTFT or applicable output tokens are zero or negative
- **WHEN** the dashboard renders request logs
- **THEN** it does not show a calculated TPS value

#### Scenario: Estimated gateway speed

- **WHEN** Claude or OpenRouter has a successful request with valid output and a post-TTFT window of at least one second
- **THEN** the request table and detail label its inclusive-output TPS as estimated
- **AND** the tooltip explains that shorter or unsuccessful windows are excluded

### Requirement: Reports show daily median generation speed trends

The Reports dashboard MUST expose daily median TTFT, daily median TPS, and daily median queue-wait trends when request-log latency fields are available. Empty days and rows with no valid timing/speed inputs MUST render as zero in those trend charts. Daily TPS MUST median per-request non-reasoning output-token TPS after TTFT for native and generic sources; unknown reasoning-token usage MUST be treated as zero for those sources. Claude and OpenRouter samples MUST use inclusive reported output and the same successful, nonnegative-TTFT, one-second-minimum policy as request logs. Reports and conversation analytics MUST explain that gateway speeds are estimates and exclude invalid samples without changing request or token totals. Daily queue wait MUST median per-request `latency_queue_ms` over rows where it is non-null.

#### Scenario: Daily speed charts use median valid request values

- **GIVEN** one report day has request logs with TTFT and output-token TPS values
- **WHEN** the dashboard renders Reports
- **THEN** it shows a Time to First Token chart using median TTFT for the day
- **AND** it shows a Tokens per Second chart using median per-request TPS for the day

#### Scenario: Invalid daily speed samples are excluded

- **GIVEN** a report day contains rows where total latency is less than or equal to TTFT or applicable output tokens are zero or negative
- **WHEN** the daily TPS median is calculated
- **THEN** those rows are excluded from the median

#### Scenario: Missing daily speed data is zero-filled

- **GIVEN** a selected report range includes a day with no request logs or no valid timing data
- **WHEN** the dashboard renders Reports
- **THEN** the TTFT and TPS charts include that day with value zero

#### Scenario: Daily queue-wait trend surfaces load-balancer wait

- **GIVEN** a report day has request logs with non-null `latency_queue_ms`
- **WHEN** the dashboard renders Reports
- **THEN** it shows a queue-wait trend using the day's median `latency_queue_ms`
- **AND** days without queue samples render as zero

#### Scenario: Gateway burst excluded from aggregates

- **WHEN** a Claude or OpenRouter request has a post-TTFT window shorter than 1000 ms
- **THEN** Reports and conversation analytics exclude its TPS while retaining valid TTFT and usage observations

### Requirement: Request speed timings share one anchor and expose queue wait

For a single request-log row, `latency_ms` and `latency_first_token_ms` MUST be
measured from the same anchor: the start of the attempt that produced the row.
Time spent before that attempt — account selection, admission waits, and failed
failover attempts — MUST NOT inflate `latency_first_token_ms`; the HTTP
streaming path MUST record it instead in a nullable `latency_queue_ms`.
First-token detection MUST treat the first token-bearing output event — visible text, refusal, reasoning deltas, function-call argument, custom-tool input, tool-call output, or a custom/apply-patch tool-call `response.output_item.added` or `response.output_item.done` event with meaningful tool-call payload content when the tool protocol does not stream argument deltas — as the first token. Lifecycle/control events, reasoning-summary placeholder deltas stripped before delivery, and metadata-only or empty tool-call deltas or completion events MUST NOT record first-token latency. TTFT means time to first model output and the generation window (`latency_ms - latency_first_token_ms`) covers reasoning generation, while native/generic TPS uses the non-reasoning output-token numerator. Claude and OpenRouter SHALL use their estimated inclusive-output throughput policy instead.

#### Scenario: Failover no longer inflates TTFT

- **GIVEN** a streaming request fails over from one account and succeeds on the
  next attempt
- **WHEN** the request log is persisted
- **THEN** `latency_first_token_ms` reflects only the successful attempt
- **AND** `latency_queue_ms` records the pre-attempt time (selection plus the
  failed attempt)
- **AND** `latency_ms` is greater than or equal to `latency_first_token_ms`

#### Scenario: Non-placeholder reasoning delta counts as the first token

- **GIVEN** an upstream stream emits a non-placeholder, token-bearing reasoning summary delta before the first visible text delta
- **WHEN** first-token latency is captured
- **THEN** `latency_first_token_ms` anchors to the reasoning delta rather than waiting for visible text

#### Scenario: Single-anchor rows on websocket and bridge paths

- **WHEN** a websocket or HTTP bridge request records latency timings
- **THEN** `latency_ms` and `latency_first_token_ms` derive from the same
  request-state anchor
- **AND** `latency_queue_ms` MAY be null on paths whose queue waits are already
  recorded in dedicated phase columns
