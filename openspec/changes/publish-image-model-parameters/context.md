## Sources

The OpenAI table follows the Images API reference for `POST /images/generations` and `POST /images/edits` and the
image generation guide, read on 2026-11-27:

- GPT Image 2.6 (Sunburst, Flare): quality up to `max`, `complexity` (default `high`), custom sizes, PNG, JPEG,
  WebP, GIF and SVG output, `frame_count` and `frame_duration_ms` for GIF.
- GPT Image 2.5 (Sunburst, Flare and their `2026-09-08` snapshots): quality up to `max`, custom sizes, PNG, JPEG and
  WebP output; resolutions above 2560x1440 are experimental.
- GPT Image 2 (and `2026-04-21`): quality up to `high`, custom sizes, transparent background in preview.

OpenAI's `/models` list carries no parameter information, so the table must be revised when OpenAI documents a new
family. Models outside the table publish no `supported_parameters`: an absent description means "not documented here",
never "accepts nothing".

`markup` and `input_fidelity` are omitted. codex-lb's multipart edit route accepts only `image` and `mask` files,
and OpenAI requires `input_fidelity` to be omitted for GPT Image 2 and later.

## Native gpt-image-2

The native ChatGPT image endpoint is reached with the subscription. Its parameter support is not documented, and
codex-lb does not probe it. The description lists what the Codex client itself sends there: `background` (`opaque`
or `transparent`), `quality: auto` and `size: auto`. Other fields still pass through unchanged.

## Example

```json
{
  "id": "openai-apikey/gpt-image-2.6-sunburst",
  "api_types": ["images"],
  "image": {
    "id": "gpt-image-2.6-sunburst",
    "supported_parameters": {
      "complexity": {"type": "enum", "values": ["low", "medium", "high"], "default": "high"},
      "frame_count": {"type": "range", "min": 2, "max": 16, "default": 9, "description": "GIF output only."}
    }
  }
}
```
