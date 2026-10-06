# Tasks

## 1. Implementation

- [x] 1.1 `project_phases` holds a phase-less assistant message's `output_item.done` until the next output item or
  the terminal decides its phase, and mirrors the phases into the terminal response output.
- [x] 1.2 `assign_phases` applies the same rule to non-streamed OpenRouter Responses.
- [x] 1.3 Streamed and non-streamed OpenRouter Responses forwarding apply the projection; tool-name restoration shares
  its SSE framing.

## 2. Verification

- [x] 2.1 Unit tests for commentary before later output, final answer, tool-requesting responses, incomplete and
  failed responses, upstream phase passthrough and stream failure.
- [x] 2.2 Integration test: a Codex WebSocket turn over an OpenRouter account receives the phases on
  `output_item.done` and `response.completed`, and the next turn's replayed history keeps them.
- [x] 2.3 ruff, ty, pytest, strict OpenSpec validation.
