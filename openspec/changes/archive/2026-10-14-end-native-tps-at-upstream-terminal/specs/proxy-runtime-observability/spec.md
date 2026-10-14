## MODIFIED Requirements

### Requirement: Request speed timings share one anchor and expose queue wait

For a single request-log row, `latency_ms`, `latency_first_token_ms` and
`latency_upstream_terminal_ms` MUST be measured from the same anchor: the start
of the attempt that produced the row. Time spent before that attempt — account
selection, admission waits, and failed failover attempts — MUST NOT inflate
`latency_first_token_ms`; the HTTP streaming path MUST record it instead in a
nullable `latency_queue_ms`. `latency_upstream_terminal_ms` MUST record when the
upstream terminal event arrived; it MUST NOT include settlement, request-log
persistence or downstream delivery after that event.
First-token detection MUST treat the first token-bearing output event — visible text, refusal, reasoning deltas, function-call argument, custom-tool input, tool-call output, or a custom/apply-patch tool-call `response.output_item.added` or `response.output_item.done` event with meaningful tool-call payload content when the tool protocol does not stream argument deltas — as the first token. Lifecycle/control events, reasoning-summary placeholder deltas stripped before delivery, and metadata-only or empty tool-call deltas or completion events MUST NOT record first-token latency. TTFT means time to first model output and the generation window (`latency_upstream_terminal_ms - latency_first_token_ms`) covers reasoning generation, while native/generic TPS uses the non-reasoning output-token numerator. Rows without an upstream-terminal latency MUST use `latency_ms` as the end of their generation window. Claude and OpenRouter SHALL use their estimated inclusive-output throughput policy instead.

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

#### Scenario: TPS ends at the upstream terminal

- **GIVEN** a native request with first-token latency 1,000 ms, upstream-terminal latency 3,000 ms, `latency_ms` 5,000 ms and 200 non-reasoning output tokens
- **WHEN** its TPS is computed
- **THEN** TPS is 100 tokens per second

#### Scenario: Historical rows keep their recorded end

- **GIVEN** a native row without an upstream-terminal latency
- **WHEN** its TPS is computed
- **THEN** the generation window ends at `latency_ms`
