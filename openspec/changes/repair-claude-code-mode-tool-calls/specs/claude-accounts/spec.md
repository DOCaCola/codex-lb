## MODIFIED Requirements

### Requirement: Bounded undeclared Claude tool diagnostics
Claude tool calls SHALL resolve by wire name, or by the client's own qualified tool name when exactly one tool in the request has it. Under Codex code mode, an otherwise unresolved call naming a nested code-mode helper or a direct `mcp__<server>__<tool>` SHALL resolve as that helper's code-mode `exec` program. Other names, including a client name shared by several tools, SHALL fail explicitly without further alias guessing or client-side execution. Diagnostics SHALL identify source, model, response, content index, declaration count and a bounded name fingerprint; a bounded syntactically safe tool name MAY also be recorded. Arguments, call IDs, conversation contents and credentials MUST NOT be logged.

#### Scenario: Unknown tool after text
- **WHEN** Claude emits an undeclared tool after an assistant progress message
- **THEN** the tool is rejected with content-free identity diagnostics and no tool-call event for that tool reaches the client

#### Scenario: Unsafe name
- **WHEN** the rejected name contains control characters, unsupported characters or excessive length
- **THEN** only its fingerprint and safe structural metadata are logged

#### Scenario: Client name used by Claude
- **WHEN** Claude calls `write_stdin` and the request declared exactly one tool with that name
- **THEN** the call resolves to that tool

#### Scenario: Ambiguous client name
- **WHEN** Claude calls a client name that several declared tools share
- **THEN** the call is rejected as undeclared

## ADDED Requirements

### Requirement: Claude code-mode helper recovery
When a translated request declares Codex code mode, a Claude call that resolves to no declared tool and names `exec_command`, `shell_command`, `write_stdin`, `apply_patch`, `view_image`, `create_goal`, `get_goal`, `update_goal` or a direct `mcp__<server>__<tool>` with both parts present SHALL reach the client as a call to the declared `exec` tool. Its input SHALL be a program that awaits that nested helper and passes the result to `text()`: `shell_command` SHALL call `exec_command` with `command` renamed to `cmd`; `view_image` SHALL take `file_path`, `file` or `image_path` as `path` and show an image result with `image()`; `apply_patch` SHALL take its freeform body as one string. Arguments MUST be serialized as data and never interpolated as source. Requests without code mode SHALL keep rejecting these names as undeclared.

#### Scenario: Shell helper called by name
- **GIVEN** a code-mode request
- **WHEN** Claude calls `exec_command` with `{"cmd":"git status"}`
- **THEN** the client receives an `exec` call whose program is `const result = await tools.exec_command({"cmd":"git status"});` followed by `text(result);`

#### Scenario: Flat tool surface
- **GIVEN** a request that declares `exec` beside a bare `exec_command`
- **WHEN** Claude calls `write_stdin` and no tool has that name
- **THEN** the call is rejected as undeclared

#### Scenario: Recovered call in later history
- **WHEN** a recovered call returns in conversation history
- **THEN** it is sent to Claude as a call to `Exec` with the compiled program

### Requirement: Claude freeform tool input repair
A Claude call to a freeform tool SHALL take its body from `input`. For the bare `exec` and `apply_patch` tools, a call without `input` SHALL take exactly one string among that tool's alternate fields: `code`, `script`, `js`, `javascript`, `command`, `cmd` or `content` for `exec`, and `patch` or `content` for `apply_patch`. An outer Markdown fence around the whole body SHALL be removed. An empty object SHALL be an empty body, and any other unreadable body SHALL reach the tool as the JSON Claude sent, so the tool reports the failure to the model. Under code mode, an `exec` body that is exactly one complete patch with an Add, Update or Delete file operation SHALL become a program calling `tools.apply_patch` with it; JavaScript that merely contains a patch SHALL pass through byte-identical. Decorated outer delimiters `*** Begin Patch ***` and `*** End Patch ***` of one complete patch SHALL be restored; patch content MUST NOT change. Namespaced freeform tools SHALL receive their body without these repairs. Every repaired call SHALL log source, model, response, content index, tool, recovered helper and repair kinds. A code-mode `exec` body that is a JSON shell call SHALL be recorded in that log and not rewritten. The log MUST NOT contain arguments or bodies.

#### Scenario: Body under another field
- **WHEN** Claude calls code-mode `Exec` with `{"code":"text(1)"}`
- **THEN** the client receives `text(1)` and the repair is logged as `field_code`

#### Scenario: Unreadable body
- **WHEN** Claude calls `Exec` with both `code` and `script` and no `input`
- **THEN** the client receives Claude's JSON as the body, never an empty body

#### Scenario: Patch sent as the program
- **GIVEN** a code-mode request
- **WHEN** Claude's `Exec` body is exactly one complete patch
- **THEN** the client receives a program calling `tools.apply_patch` with that patch

#### Scenario: Program that contains a patch
- **WHEN** an `Exec` body is JavaScript holding a patch in a string
- **THEN** it reaches the client byte-identical and nothing is logged

#### Scenario: Shell-shaped body
- **WHEN** a code-mode `Exec` body is `{"command":"npm test"}` inside `input`
- **THEN** the body reaches the client unchanged and the log records it as shell-shaped without its command
