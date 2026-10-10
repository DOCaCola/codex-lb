## ADDED Requirements

### Requirement: Translated Claude tool IDs are portable

When the service projects Responses tool calls and their outputs into Claude
Messages, it SHALL write each `call_id` as a wire ID matching
`^[a-zA-Z0-9_-]+$`. A call ID already matching that pattern SHALL pass
unchanged unless it starts with the reserved prefix `cxlb_tid_v1_`; every other
call ID SHALL become that prefix followed by the unpadded base64url encoding of
its UTF-8 bytes. A tool call and its result SHALL use the same wire ID, and
distinct call IDs SHALL never share one. Tool-cycle pairing and validation
SHALL use the original call IDs.

#### Scenario: Foreign call ID from another provider

- **GIVEN** history containing a tool call and output with call ID `functions.shell:0`
- **WHEN** the request is projected for Claude
- **THEN** the `tool_use.id` and the `tool_result.tool_use_id` are both
  `cxlb_tid_v1_ZnVuY3Rpb25zLnNoZWxsOjA`

#### Scenario: Claude's own call ID is unchanged

- **GIVEN** history containing a tool call with call ID `toolu_01Abc-d_E`
- **WHEN** the request is projected for Claude
- **THEN** the `tool_use.id` is `toolu_01Abc-d_E`

#### Scenario: Reserved prefix cannot collide

- **GIVEN** history containing a call ID that already starts with `cxlb_tid_v1_`
- **WHEN** the request is projected for Claude
- **THEN** that call ID is encoded and its wire ID differs from every other
  call's wire ID
