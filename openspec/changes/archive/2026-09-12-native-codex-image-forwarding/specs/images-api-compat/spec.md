## ADDED Requirements

### Requirement: Native Codex image forwarding
Codex-base image routes SHALL forward JSON to the same native ChatGPT image operation using a scoped account, without Responses conversion or model-source fallback. They MUST enforce proxy authorization, public image model policy, request limits and account admission. They MUST preserve upstream response bytes, status and safe image metadata headers, MUST NOT follow redirects carrying credentials, and MUST NOT replay after dispatch. Reservation cleanup MUST retain tracked ownership on errors and cancellation; only reported usage MAY be charged. Public `/v1/images/*` behavior MUST remain unchanged.

#### Scenario: Native edit is independent of conversation model
- **WHEN** Codex sends an image edit while its conversation uses a model source
- **THEN** the original JSON is sent to a permitted ChatGPT account's `/codex/images/edits` endpoint without selecting a Responses host

#### Scenario: Native failure remains visible
- **WHEN** the upstream image endpoint returns an error status and body
- **THEN** the same status and body reach the client without an image retry or API-credit fallback

#### Scenario: Native success preserves metadata
- **WHEN** upstream returns image bytes, generation IDs and an image request ID
- **THEN** the response bytes and image request ID are preserved for Codex

## REMOVED Requirements

### Requirement: Codex-base Images API aliases
**Reason**: Native Codex operations must not enter the public Responses adapter.
**Migration**: Existing Codex URLs remain unchanged and now forward native JSON. Public `/v1/images/*` is unchanged.

## MODIFIED Requirements

### Requirement: Internal host selection
Public `/v1/images/*` generation and edit adapters MUST select the first candidate with nonempty registry plan visibility and no suppression, ordered as `gpt-5.6-luna`, `gpt-5.5`. If none qualifies, they MUST use `gpt-5.6-luna`. Public image model IDs MUST remain unchanged. Native Codex image routes MUST NOT select an internal host.

#### Scenario: Cold registry prefers the current host
- **WHEN** the registry uses the bootstrap catalog
- **THEN** the internal model is `gpt-5.6-luna`

#### Scenario: Preferred model unavailable in registry
- **WHEN** only `gpt-5.5` has registry plan visibility without suppression
- **THEN** the internal model is `gpt-5.5`

#### Scenario: No candidate qualifies
- **WHEN** neither candidate has plan visibility without suppression
- **THEN** the selected host is `gpt-5.6-luna` and existing downstream error handling applies
