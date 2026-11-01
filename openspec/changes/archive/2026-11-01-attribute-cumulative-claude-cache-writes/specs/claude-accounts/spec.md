## MODIFIED Requirements

### Requirement: Claude request usage and timing
Claude native and adapted request logs SHALL preserve inclusive input/output tokens, separately reported cache reads and writes, and only provider-reported reasoning tokens. When a cumulative stream usage update changes the cache-write total without restating its 5-minute/1-hour split, the whole total SHALL be attributed to the single cache lifetime used by every cache marker of the dispatched body; with mixed or absent lifetimes the split SHALL become unknown rather than keep the earlier, partial split. The gateway SHALL measure upstream-attempt duration and time to first nonempty generated text, thinking or tool payload from a monotonic pre-open anchor. Nonempty redacted-thinking data and thinking signatures SHALL establish opaque first output. Metadata, pings and empty deltas MUST NOT establish first-token latency. Error, cancellation and truncated streams SHALL finalize duration without inventing first-token latency. Timing observation MUST precede Responses adaptation and MUST NOT expose opaque contents or infer reasoning token counts.

#### Scenario: Cached thinking stream
- **WHEN** a stream reports uncached input, cache reads, cache writes and output but no reasoning token count
- **THEN** its inclusive totals and cache breakdown persist, while reasoning tokens remain unknown

#### Scenario: Server-side sampling rounds raise cache writes
- **WHEN** a request whose cache markers all use the 1-hour lifetime receives a final usage update with a larger cache-write total and no split
- **THEN** all cache writes are recorded and priced as 1-hour writes
- **AND** a request with mixed lifetimes records the total with an unknown split and an unknown cost

#### Scenario: Opaque first output
- **WHEN** a native stream emits nonempty redacted-thinking data or a thinking signature before visible output
- **THEN** TTFT anchors to that opaque upstream output and completion retains the same monotonic attempt anchor
- **AND** empty opaque fields, pings and terminal events alone do not establish TTFT
