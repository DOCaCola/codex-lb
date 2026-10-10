## ADDED Requirements

### Requirement: Claude cache misses are attributed to the changed prefix part

The service SHALL remember, for each recent Claude conversation, a digest-only
shape of its latest request: per-tool digests, the system digest, digests of
the other top-level parameters, and per-message digests, all computed with
`cache_control` markers removed. When a request reports no cache read but a
cache write, and a shape exists for the same conversation or, failing that, for
its parent session, the service SHALL log which part differs from that shape:
tools added, removed, changed or reordered, a changed system, changed
parameter names, and the index and block types of the first divergent message.
Requests that read from the cache, and misses without an earlier shape, SHALL
log nothing. Shapes SHALL contain no request content.

#### Scenario: Fork drops a tool

- **GIVEN** a parent session whose latest request declared tools `exec` and `create_canvas`
- **WHEN** a forked conversation from that session sends only `exec` and reports no cache read but a cache write
- **THEN** the service logs the parent as reference and `create_canvas` as removed

#### Scenario: Moved breakpoints are not a divergence

- **GIVEN** a conversation whose next request appends messages and moves its cache breakpoints
- **WHEN** that request reports no cache read but a cache write
- **THEN** the logged tools and system are unchanged and no message diverges

#### Scenario: Cache hit is silent

- **GIVEN** a conversation with a remembered shape
- **WHEN** its next request reports a cache read
- **THEN** the service logs nothing for it
