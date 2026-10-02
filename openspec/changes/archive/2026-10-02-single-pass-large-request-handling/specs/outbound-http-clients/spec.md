# outbound-http-clients Delta

## ADDED Requirements

### Requirement: Native helper command bodies are framed as raw bytes

A native helper command that carries a body (an HTTP request body, or a WebSocket text or binary send) MUST declare the body length as `payload_bytes` on its newline-terminated JSON command line, followed by exactly that many raw bytes. The body MUST NOT be base64-encoded or embedded in the JSON line. The helper MUST advertise the `framed_payload_v1` capability, and the Python adapter MUST require it during negotiation. The helper MUST reject a WebSocket text payload that is not valid UTF-8.

#### Scenario: A large request body reaches the origin unchanged

- **WHEN** the adapter sends an HTTP request whose body is arbitrary bytes
- **THEN** the command line declares the body length and the raw bytes follow it
- **AND** the origin receives the body byte for byte

#### Scenario: A helper without framed payloads is incompatible

- **WHEN** a helper's handshake does not report `framed_payload_v1`
- **THEN** negotiation fails as an incompatible protocol before any dispatch
