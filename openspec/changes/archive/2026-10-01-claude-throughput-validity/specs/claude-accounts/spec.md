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

## ADDED Requirements

### Requirement: Estimated Claude throughput validity
Claude TPS SHALL use total reported output tokens over the gateway-observed post-TTFT window and be identified as estimated. A sample MUST have successful status, positive reported output, nonnegative known TTFT and a window of at least one second. Dashboard, Reports and conversation analytics SHALL apply identical validity and numerator rules to existing and new logs without changing stored timings, usage or costs.

#### Scenario: Burst-delivered output
- **WHEN** a successful Claude log reports 578 output tokens, 6713 ms elapsed and 6690 ms TTFT
- **THEN** the request displays no TPS and is excluded from aggregate TPS samples
- **AND** TTFT, duration, usage and costs remain available

#### Scenario: Boundary and reasoning
- **WHEN** a successful Claude log reports 100 output tokens, 1000 ms after first output and a known or unknown reasoning count
- **THEN** estimated TPS is 100 and the aggregate includes one sample without subtracting reasoning

#### Scenario: Unsuccessful or unobserved output
- **WHEN** Claude output is unsuccessful, has no observed first output, has negative TTFT or lacks positive reported output
- **THEN** TPS is unavailable without substituting total duration or a guessed token count
