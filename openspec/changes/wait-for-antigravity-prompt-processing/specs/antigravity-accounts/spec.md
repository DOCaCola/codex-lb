## ADDED Requirements

### Requirement: Antigravity prompt processing before the first event
An Antigravity request SHALL wait up to 180 seconds for Cloud Code's response headers and up to 80 seconds after the
headers for its first event, independent of the Responses model-source deadlines. When either deadline passes, the
request SHALL fail with `model_source_timeout` and a message naming the deadline that applied. A stream that ends or
goes idle before its first event SHALL fail with `invalid_upstream_response`.

#### Scenario: Large prompt
- **WHEN** Cloud Code sends its headers 60 seconds after the request and its first event 40 seconds later
- **THEN** the request continues and streams the response

#### Scenario: Silent first event
- **WHEN** Cloud Code sends headers but no event within 80 seconds
- **THEN** the request fails with `model_source_timeout` and a message naming 80s
