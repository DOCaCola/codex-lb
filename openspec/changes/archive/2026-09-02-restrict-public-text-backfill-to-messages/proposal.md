# Restrict Public Text Backfill to Messages

## Why

The public Responses stream fallback currently extracts text from every
completed output item after normalization. OpenAI-compatible providers such as
LiteLLM can represent model reasoning as a `type: "reasoning"` item whose
`content` contains reasoning text. The fallback consequently synthesizes a
`response.output_text.delta` for that reasoning item, exposing reasoning as
assistant-visible output even though the upstream stream classified it
correctly.

## What Changes

- Synthesize missing `response.output_text.delta` events only from normalized
  assistant message items.
- Preserve reasoning events and reasoning output items without converting their
  text into visible assistant output.
- Keep the existing message-text fallback and per-item duplicate suppression.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `responses-api-compat`: public stream text backfill is explicitly limited to
  message items and must not promote reasoning-item content to visible text.

## Impact

- **Code**: `app/modules/proxy/api.py`.
- **Tests**: public stream contract and model-source route regressions using a
  LiteLLM-style interleaved reasoning/message stream.
- **Behavior**: reasoning-capable OpenAI-compatible model sources can forward
  reasoning without leaking it through `response.output_text.delta`.
