## Why

Clients that choose an image model on `/v1/images/*` cannot learn what that model accepts. OpenRouter image models
already list their endpoint capabilities on `/v1/models`, but OpenAI API image models list only their id and the
native `gpt-image-2` model is not listed at all. A client therefore has to guess which quality levels, sizes,
formats or complexity settings a model takes, and a wrong guess is a failed or wasted paid request. The codex-lb
Codex plugin's image tool needs this to describe each model to the agent.

## What Changes

- Image models on `/v1/models` carry `image.supported_parameters` in one shape for every provider: each parameter
  has a `type` (`enum`, `range`, `boolean` or `string`), its `values` or `min`/`max`, and optionally a
  `default` and a `description` for conditions such as "GIF output only".
- OpenRouter models keep publishing OpenRouter's synchronized capabilities unchanged.
- OpenAI API image models publish the parameters OpenAI's Images API reference documents for their family
  (GPT Image 2.6, 2.5, 2). A model outside these families publishes no parameters, rather than guessed ones.
- The native `gpt-image-2` model is listed with the parameters the Codex client is known to send on the native
  endpoint. With an active image redirect it is listed with the redirect target's parameters; with an inactive
  redirect it is not listed, matching request-time behavior. API-key model restrictions apply.

## Impact

- Spec: `images-api-compat`.
- Code: new `app/modules/model_sources/image_parameters.py`; `/v1/models` assembly in `app/modules/proxy/api.py`.
- No migration, no setting, no change to request handling: parameters still pass through unchanged and upstream
  validation still decides.
