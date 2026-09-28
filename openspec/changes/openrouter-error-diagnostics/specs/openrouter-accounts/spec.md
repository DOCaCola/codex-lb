## MODIFIED Requirements

### Requirement: OpenRouter errors conform to client error contracts
OpenRouter HTTP rejections MUST preserve their HTTP status and sanitized message while exposing string error codes and types to clients when provided. Responses forwarding MUST retain its upstream 401 protection: return a generic proxy-credential 502 without reading the rejected credential body. WebSocket clients MUST receive a parseable terminal error rather than wait for a completion that will never arrive.

#### Scenario: Numeric provider error code
- **WHEN** OpenRouter rejects a WebSocket-backed turn with HTTP 404 and numeric code 404
- **THEN** the client receives an error frame with status 404 and a string code and the original message

## ADDED Requirements

### Requirement: Safe OpenRouter provider diagnostics
OpenRouter HTTP 403 rejections MUST retain their status without being labeled invalid proxy credentials solely from that status. Structured nested provider reasons and provider names SHALL appear in the sanitized message visible to clients and request logs. The system MUST bound error body reads and diagnostic lengths, redact configured and recognizable credential values before truncation, and exclude arbitrary raw metadata. Existing unknown-source credential protection and OpenRouter 401 protection MUST remain unchanged.

#### Scenario: Provider rejects a request
- **WHEN** OpenRouter returns 400 with a generic message and structured provider metadata
- **THEN** clients and request logs include the sanitized provider reason without raw metadata or credential values

#### Scenario: Funding or policy denial
- **WHEN** OpenRouter returns 403 with a denial message
- **THEN** the client sees status 403 and a sanitized reason, not an assertion that credentials are invalid

#### Scenario: Unusable error body
- **WHEN** an OpenRouter error body is oversized or not valid JSON
- **THEN** the original error status is retained with a generic message and no raw body disclosure
