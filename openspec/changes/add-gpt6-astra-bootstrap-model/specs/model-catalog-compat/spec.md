## MODIFIED Requirements

### Requirement: Bootstrap model catalog is available before refresh

Before the first successful upstream model-registry refresh, the system MUST
serve a conservative static catalog of known Codex model slugs from both
`GET /v1/models` and `GET /backend-api/codex/models`. This static catalog is a
bundled fallback for startup/offline paths; refreshed upstream model-registry
data remains the authoritative source once available. A replica that starts
while a fresh persisted registry snapshot exists SHALL serve the persisted
catalog (not the bootstrap catalog) before its first scheduler tick; the
bootstrap catalog remains the floor only when no persisted or refreshed
snapshot is available. The bootstrap catalog MUST include `gpt-6-astra`,
`gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`,
`gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5.3-codex-spark`, `gpt-5.2`, and
`codex-auto-review`, and MUST NOT invent unverified variant slugs such as
`gpt-5.5-pro` or a bare `gpt-5.6`. `gpt-5.3-codex` and
`gpt-5.3-codex-spark` were dropped from upstream's bundled catalog at Codex
rust-v0.144.x but remain retained for older pinned clients because the upstream
backend still serves them.

#### Scenario: OpenAI-compatible models endpoint serves bootstrap slugs

- **GIVEN** the model registry has no refreshed upstream snapshot
- **AND** no persisted registry snapshot is available
- **WHEN** a client calls `GET /v1/models`
- **THEN** the response contains exactly the bootstrap model slugs
- **AND** the response includes `gpt-6-astra`, `gpt-5.6-sol`,
  `gpt-5.6-terra`, and `gpt-5.6-luna`
- **AND** the response does not include `gpt-5.5-pro` or bare `gpt-5.6`

#### Scenario: Codex-native models endpoint serves GPT-5.6 bootstrap metadata

- **GIVEN** the model registry has no refreshed upstream snapshot
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** the `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna` entries
  include representative upstream metadata including context-window,
  visibility, speed-tier, and reasoning fields
- **AND** Sol and Terra advertise `low`, `medium`, `high`, `xhigh`, `max`, and
  `ultra`
- **AND** Luna advertises `low`, `medium`, `high`, `xhigh`, and `max`

#### Scenario: Replica startup with a fresh persisted snapshot serves the persisted catalog

- **GIVEN** a fresh persisted registry snapshot exists whose catalog differs
  from the bootstrap catalog
- **WHEN** a replica starts and a client calls `GET /v1/models` before the first
  refresh tick
- **THEN** the response reflects the persisted catalog, not the bootstrap
  catalog

#### Scenario: Model endpoints serve Astra before refresh

- **GIVEN** the model registry has no refreshed or persisted upstream snapshot
- **WHEN** a client calls `GET /v1/models` or `GET /backend-api/codex/models`
- **THEN** the response includes `gpt-6-astra`

## ADDED Requirements

### Requirement: GPT-6 Astra bootstrap metadata matches the Codex catalog

The `gpt-6-astra` bootstrap entry MUST preserve all behavior-affecting metadata
from the catalog downloaded by Codex client 0.153.1: display name
`GPT-6-Astra`; description
`Our most capable model for complex, demanding work.`; text and image input;
`context_window=272000`; `max_context_window=872000`; default reasoning effort
`medium`; supported efforts `low`, `medium`, `high`, `xhigh`, `max`, and
`ultra`; verbosity support with default `low`; websocket preference; API
support; `shell_type="unified_exec"`; `tool_mode="code_mode_only"`;
`use_responses_lite=true`; freeform apply-patch; text-and-image search;
original image detail; `multi_agent_version="v2"`;
`multi_agent_reasoning_effort="xhigh"`; the advertised experimental tools;
Node REPL flags; usage-instruction flags; token truncation policy; effective
context percentage; compaction hash; and Fast service-tier metadata.

The bootstrap entry MUST NOT bundle the large `model_messages` payload, which
the successful live per-account catalog refresh supplies. A missing
`minimal_client_version` in the installed catalog MUST remain `null`, not be
replaced with an invented version. The bootstrap plan set is only a
pre-refresh availability floor; live per-account catalogs remain authoritative.

#### Scenario: Codex-native catalog exposes Astra client behavior

- **GIVEN** the model registry has no refreshed or persisted upstream snapshot
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** the Astra entry advertises all six supported reasoning levels
- **AND** its default reasoning level is `medium`
- **AND** its shell type is `unified_exec`
- **AND** its experimental tools are `send_user_message_async` and `clock`
- **AND** its maximum context window is `872000`
- **AND** its minimal client version is `null`

#### Scenario: OpenAI-compatible catalog keeps Astra's default input budget

- **GIVEN** the model registry has no refreshed or persisted upstream snapshot
- **WHEN** a client calls `GET /v1/models`
- **THEN** the Astra entry reports `context_window=272000` and
  `input_context_window=272000`
- **AND** the `872000` ceiling is not promoted into those input-budget fields

#### Scenario: Astra uses websocket preference before refresh

- **GIVEN** the model registry has no refreshed upstream snapshot
- **WHEN** websocket preference is checked for `gpt-6-astra` or a dated
  `gpt-6-*` Astra-family slug
- **THEN** the lookup returns true
