## ADDED Requirements

### Requirement: Native collaboration tools exchange plaintext messages
Native ChatGPT Responses requests SHALL declare a client namespace named `collaboration` upstream as `collaboration-optimize`, without `encrypted` markers on its tool parameters, in top-level `tools` and in `additional_tools` input bundles. Other tools and history items SHALL be forwarded unchanged. Before any other processing, native output SHALL restore every `collaboration-optimize` function call to namespace `collaboration` with `encrypted_function_args: []`, and every echoed namespace declaration to `collaboration`. This SHALL hold over HTTP, the upstream WebSocket and the HTTP bridge.

#### Scenario: Child reports to its parent
- **WHEN** an OpenAI-served agent calls `send_message`
- **THEN** the client receives a `collaboration` call with a plaintext `message` and `encrypted_function_args: []`, and the recipient receives plaintext whatever its provider

#### Scenario: Incremental WebSocket turn without tools
- **WHEN** an upstream response on a continued WebSocket turn contains a `collaboration-optimize` call
- **THEN** the client receives it as a `collaboration` call
