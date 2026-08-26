## ADDED Requirements

### Requirement: Source-owned terminal compaction uses the selected model source

Terminal compaction requests SHALL participate in Responses model-source
selection on the HTTP route. A selected source SHALL receive an ordinary,
non-streaming summarization request rather than the private
`compaction_trigger` protocol. The request MUST omit tools, tool choice,
parallel tool calls, input-carried `additional_tools`, structured-output
controls, continuation identifiers, and the terminal trigger; it MUST append
the Codex handoff-summary instruction and replace image inputs with an explicit
omission marker.

When a model source receives replayed compaction history that was minted by a
native backend and cannot be decoded by codex-lb, the proxy MUST replace that
opaque item with an explicit unavailable-history note rather than forwarding
it to the source.

#### Scenario: Source model summarizes through its normal Responses API

- **GIVEN** an enabled Responses-capable model source serves model `m`
- **WHEN** the HTTP Responses request for `m` ends with a terminal
  `compaction_trigger`
- **THEN** the selected source receives a normal non-streaming Responses request
- **AND** it receives neither the trigger nor any top-level or input-carried
  tool surface

#### Scenario: Native opaque history switches to a source

- **GIVEN** input contains a native compaction item that codex-lb cannot decode
- **WHEN** the next request is routed to a model source
- **THEN** the source receives an explicit unavailable-history note
- **AND** it does not receive the opaque encrypted item
