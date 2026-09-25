## ADDED Requirements

### Requirement: Model capability filters
The model selector SHALL offer text generation, image generation, vision, tools, and reasoning filters based on catalog metadata. Multiple filters MUST match all selected capabilities and combine with name/ID search. Filtering MUST NOT change selected models, including unavailable selections. Operators MUST be able to clear capability filters and see explicit empty-result feedback.

#### Scenario: Filter image models with reference input
- **WHEN** an operator selects image generation and vision filters
- **THEN** only models with image generation metadata and image input support are shown, without removing hidden selections

### Requirement: Image catalog selection
The system SHALL synchronize OpenRouter's dedicated image catalog and selected image models' endpoint capabilities and pricing. Image selections MUST remain explicit and persist through refresh. Image-only models MUST be discoverable through `/v1/models` but MUST NOT be advertised as Codex conversation models or dispatched as chat/Responses models. The account model selector MUST distinguish images from text and display image billable units instead of fictitious text context or token caps.

#### Scenario: Selected image model
- **WHEN** an operator selects an available image model
- **THEN** public model discovery includes it, while the Codex conversation catalog excludes it

### Requirement: Public image routing
Public `/v1/images/generations` and multipart `/v1/images/edits` SHALL route explicitly selected `openrouter/` image models to OpenRouter's `/images` endpoint. The adapter MUST preserve the selected model, translate reference uploads to data URLs, validate endpoint capabilities, and reject unsupported parameters including masks without silent dropping. Native Codex image endpoints and bare OpenAI image model behavior MUST remain unchanged.

#### Scenario: Reference image editing
- **WHEN** a client edits using an enabled OpenRouter image model and uploaded reference images
- **THEN** the adapter forwards those references as `input_references` and returns base64 image results

### Requirement: Image lifecycle and accounting
Image dispatch MUST enforce model/source restrictions, pause state, cooldowns and request limits; it MUST NOT fall through to subscription accounts or retry non-idempotent image generation. Responses MUST use bounded memory, preserve upstream errors and Retry-After, terminate incomplete streams with an error, release connections on cancellation, and settle reservations exactly once. Completed usage MUST retain OpenRouter's reported dollar cost and token counts. Unknown cost MUST NOT be fabricated as zero. Partial images alone MUST NOT be billed as completed work.

#### Scenario: Streaming completion
- **WHEN** OpenRouter sends partial images followed by completion
- **THEN** the client receives Images SSE events and final usage is recorded once

#### Scenario: Native Codex generation
- **WHEN** a Codex-native client requests gpt-image-2
- **THEN** the existing native ChatGPT path is used without an OpenRouter override
