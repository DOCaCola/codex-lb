## ADDED Requirements

### Requirement: Source error bodies keep their text
When a model source answers an error status with a non-JSON body, every forwarding path, including native Claude Messages, SHALL keep the upstream status and the `model_source_error` code and SHALL use the body's text as the message. HTML SHALL contribute its unescaped page title; other text SHALL be whitespace-collapsed, redacted and truncated to 1000 characters. HTML without a title and undecodable bodies SHALL use the generic provider message.

#### Scenario: Edge error page
- **WHEN** a source returns 503 with an HTML page titled "503 Service Unavailable"
- **THEN** the client and request log see status 503, code `model_source_error` and message "503 Service Unavailable"

#### Scenario: Plain-text error
- **WHEN** a source returns 502 with the plain-text body "upstream connect error"
- **THEN** the error message is "upstream connect error"

#### Scenario: Native Claude error page
- **WHEN** a native Claude Messages request receives a non-JSON 503
- **THEN** the client receives an Anthropic error with status 503 and the page's text, not an invalid-JSON error

### Requirement: Bounded source error body reads
Error bodies SHALL be read within the source's first-frame deadline and up to 64KiB. Oversized, timed-out or unreadable bodies, and JSON bodies without an error object, SHALL keep the upstream status with the generic provider message.

#### Scenario: Oversized error body
- **WHEN** a source error body exceeds 64KiB
- **THEN** the upstream status is kept with the generic provider message

#### Scenario: Stalled error body
- **WHEN** a source sends error headers but its body does not arrive before the first-frame deadline
- **THEN** the upstream status is kept with the generic provider message
