## ADDED Requirements

### Requirement: Claude models use Codex code mode

The model catalog SHALL advertise `tool_mode: code_mode_only` for Claude
models. When a translated request declares Codex's un-namespaced freeform `exec`
tool and no un-namespaced `exec_command` or `shell_command` function, the service
SHALL append the code-mode contract to the system instructions after the
client's instructions. The contract SHALL name the `exec` tool by its wire name
and SHALL NOT list the request's other tools, so it is identical for every tool
set. Requests without Codex code mode SHALL NOT receive it.

#### Scenario: Code-mode request

- **GIVEN** a Codex request with instructions that declares the freeform `exec` tool
- **WHEN** it is sent to a Claude account
- **THEN** the instructions are followed by the code-mode contract naming `Exec`, wherever OAuth instruction placement puts them

#### Scenario: Flat tool surface

- **GIVEN** a request that declares `exec` alongside a bare `exec_command`, or declares no freeform `exec`
- **WHEN** it is projected for Claude
- **THEN** no code-mode contract is added

## MODIFIED Requirements

### Requirement: Portable standalone tool-output context
Translated Claude Responses over HTTP and WebSocket SHALL preserve a function/custom-tool output with a nonempty call identifier and no corresponding call anywhere in the expanded input as explicitly labeled user context, including supported text and images. The label SHALL identify the original output kind and call identifier. Projection MUST NOT invent a tool call, tool result or signed reasoning, and MUST NOT mutate retained logical history. Real tool results SHALL remain paired exactly once with preceding pending calls. A later `custom_tool_call_output` for an answered code-mode `exec` call, while no call is pending, is a code-mode notification: it SHALL extend that call's `tool_result` while the result is in the open result turn, and SHALL otherwise be labeled user context naming the call's tool-use identifier after the newest results. Malformed identifiers, other duplicate paired results, outputs preceding their calls and interrupted or incomplete tool cycles MUST fail before dispatch. Standalone context MUST NOT discharge an active pending call. Rejection diagnostics SHALL include the request identifier, item index, output kind, classification, a bounded call-identifier fingerprint and pending-call count, without content or credentials. Native Messages and authenticated continuation/ownership rules SHALL remain unchanged.

#### Scenario: Delegation context without a call
- **WHEN** a Codex request begins with standalone tool output followed by a user instruction
- **THEN** Claude receives labeled user context containing the output and instruction, not an orphan tool_result

#### Scenario: Valid tool continuation
- **WHEN** a retained previous response contains the call corresponding to the submitted output
- **THEN** continuation expansion restores the pair and Claude receives a real tool_use/tool_result cycle

#### Scenario: Duplicate or out-of-order output
- **WHEN** an output repeats a consumed result of anything but a code-mode `exec` call, or precedes its corresponding call
- **THEN** the request fails before upstream dispatch with content-free classification diagnostics

#### Scenario: Code-mode notification
- **WHEN** a code-mode `exec` call's result is followed by a further output for the same call
- **THEN** the notification joins that call's tool_result if no assistant step followed it, and otherwise follows the newest results as labeled context

#### Scenario: Incomplete active cycle
- **WHEN** standalone output arrives while a different call remains pending
- **THEN** the request fails without inventing a result or treating standalone context as completion of that call
