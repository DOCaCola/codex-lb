# Project Messages Effort Onto Model Levels

## Why

Claude Code's reasoning controls do not map onto every OpenAI model's effort levels. The Messages translation sent
disabled thinking as `none`, which no OpenAI catalog model accepts, and passed `output_config.effort: max` unchanged,
which GPT-5.2 through 5.5 reject because they stop at `xhigh`. Source models such as OpenRouter's can declare uneven
levels (for example low, high and max), so a valid Claude effort can still be unsupported there.

CLIProxyAPI's thinking validation (`internal/thinking/validate.go`) clamps a level to the nearest one the target
model supports, preferring the lower on a tie, when the client and model belong to different provider families, and
maps disabled thinking to the lowest level on models that cannot disable reasoning. Same-family requests stay strict.
opencodex c2f3d8b42 clamps native efforts to the selected model's ladder.

## What Changes

- The Messages translation projects the derived effort onto the target model's supported levels: the nearest level,
  the lower one on a tie, with `none` below the lowest level. Supported efforts pass through. A model without declared
  levels and unknown effort values keep the requested value.
- The levels come from the catalog entry that serves the model: the native model registry, otherwise the enabled source
  catalog visible to the API key.
- Each projection logs `messages_reasoning_effort_projected` with the model and both efforts.

Native Responses clients are unchanged: an unsupported effort reaches upstream, which rejects it with the supported
values, matching CLIProxyAPI's same-family behaviour.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `messages-api-compat`: Messages reasoning controls project onto the model's levels.

## Impact

- `app/core/messages/translate.py`, `app/modules/proxy/api.py`.
- No setting, schema or dashboard change.
