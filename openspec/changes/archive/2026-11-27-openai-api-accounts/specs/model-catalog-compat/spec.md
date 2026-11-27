## MODIFIED Requirements

### Requirement: Redirects are validated when stored

Redirects MUST be stored one row per requested model in `model_redirects` (`source_model`, `target_model`).
A write MUST be rejected with 400 `model_redirect_invalid` and a reason, without writing, unless the source
is a valid slug different from the target, the target is not itself a redirect source, and either the target is a
catalogue model servable for text generation and the source is not an image model slug, or the source is a
`gpt-image-*` slug and the target is an enabled OpenAI API image model.

#### Scenario: Redirecting a retired model
- **GIVEN** `gpt-5.4` is not in the model registry and `gpt-5.5` is a native catalogue model
- **WHEN** a redirect `gpt-5.4 -> gpt-5.5` is stored
- **THEN** it is accepted

#### Scenario: Chains and self-redirects are rejected
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** `gpt-5.3 -> gpt-5.4` or `gpt-5.5 -> gpt-5.5` is stored
- **THEN** the response is 400 with code `model_redirect_invalid` and no row is written

#### Scenario: Redirecting the image backend
- **GIVEN** `openai-apikey/gpt-image-2.5-sunburst` is an enabled OpenAI API image model
- **WHEN** a redirect `gpt-image-2 -> openai-apikey/gpt-image-2.5-sunburst` is stored
- **THEN** it is accepted

#### Scenario: Mixed redirects are rejected
- **WHEN** `gpt-image-2 -> gpt-5.5` or `gpt-5.4 -> openai-apikey/gpt-image-2.5-sunburst` is stored
- **THEN** the response is 400 with code `model_redirect_invalid`

### Requirement: Redirects cover text-generation surfaces

Redirects MUST apply to Codex Responses over HTTP and WebSocket (owner-forwarded, non-streaming,
`/responses/compact`, compaction-trigger turns and client prewarm), `/v1/responses`, `/v1/chat/completions`,
and Anthropic `/v1/messages` and `count_tokens`. The Codex and `/v1` image routes MUST apply image redirects.
Transcriptions, embeddings, realtime and internal jobs MUST NOT be redirected.

#### Scenario: Chat completions
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** a client calls `/v1/chat/completions` with `gpt-5.4`
- **THEN** `gpt-5.5` serves it

#### Scenario: Image requests
- **GIVEN** a redirect `gpt-image-2 -> openai-apikey/gpt-image-2.5-sunburst`
- **WHEN** a Codex client generates an image with `gpt-image-2`
- **THEN** the OpenAI API account serves it with `gpt-image-2.5-sunburst`
