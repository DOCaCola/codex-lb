## MODIFIED Requirements

### Requirement: Safe OpenRouter provider diagnostics
OpenRouter HTTP 403 rejections MUST retain their status without being labeled invalid proxy credentials solely from that status. Structured nested provider reasons and provider names SHALL appear in the sanitized message visible to clients and request logs. The system MUST bound error body reads and diagnostic lengths, redact configured and recognizable credential values before truncation, and exclude arbitrary raw metadata. Existing unknown-source credential protection and OpenRouter 401 protection MUST remain unchanged.

#### Scenario: Provider rejects a request
- **WHEN** OpenRouter returns 400 with a generic message and structured provider metadata
- **THEN** clients and request logs include the sanitized provider reason without raw metadata or credential values

#### Scenario: Funding or policy denial
- **WHEN** OpenRouter returns 403 with a denial message
- **THEN** the client sees status 403 and a sanitized reason, not an assertion that credentials are invalid

#### Scenario: Unusable error body
- **WHEN** an OpenRouter error body is oversized, or is JSON without an error object
- **THEN** the original error status is retained with a generic message and no raw body disclosure

#### Scenario: Non-JSON error body
- **WHEN** OpenRouter returns an HTML error page
- **THEN** the original error status is retained and the message is the page title
