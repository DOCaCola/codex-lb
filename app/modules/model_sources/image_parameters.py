"""Request parameters of image models, as published on ``/v1/models``.

OpenRouter publishes each image model's capabilities and codex-lb forwards them. OpenAI's model list describes no
parameters, so codex-lb carries what OpenAI's Images API reference documents for each GPT Image family. A model
outside these families publishes no description: absent means "not documented here", never "accepts nothing".
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.core.openai.model_registry import UpstreamModel
from app.core.types import JsonValue


class ImageParameter(BaseModel):
    type: Literal["enum", "range", "string"]
    values: list[str] = []
    min: int | None = None
    max: int | None = None
    default: str | int | None = None
    description: str | None = None


def _enum(values: list[str], default: str | None = None, description: str | None = None) -> ImageParameter:
    return ImageParameter(type="enum", values=values, default=default, description=description)


def _range(minimum: int, maximum: int, default: int | None = None, description: str | None = None) -> ImageParameter:
    return ImageParameter(type="range", min=minimum, max=maximum, default=default, description=description)


_STANDARD_SIZES = ["auto", "1024x1024", "1536x1024", "1024x1536"]
_CUSTOM_SIZE = (
    "auto, a listed size, or WIDTHxHEIGHT: both multiples of 16, aspect ratio between 1:3 and 3:1, "
    "each edge at most 3840 and 655,360 to 8,294,400 pixels in total."
)
_TRANSPARENT = "transparent needs output_format png or webp."


def _family(
    *,
    quality: list[str],
    formats: list[str],
    size: str,
    background: str,
    output_format: str | None = None,
) -> dict[str, ImageParameter]:
    return {
        "quality": _enum(quality, "auto"),
        "size": ImageParameter(type="string", values=_STANDARD_SIZES, default="auto", description=size),
        "background": _enum(["auto", "opaque", "transparent"], "auto", background),
        "output_format": _enum(formats, "png", output_format),
        "output_compression": _range(0, 100, 100, "JPEG or WebP output only."),
        "n": _range(1, 10, 1),
        "moderation": _enum(["auto", "low"], "auto"),
        "partial_images": _range(0, 3, 0, "Streaming only."),
        "input_references": _range(1, 16, description="Source images of an edit."),
    }


_GPT_IMAGE_2_6 = {
    **_family(
        quality=["auto", "low", "medium", "high", "xhigh", "max"],
        formats=["png", "jpeg", "webp", "gif", "svg"],
        size=_CUSTOM_SIZE + " For GIF output, the size of each frame.",
        background=_TRANSPARENT,
        output_format=(
            "svg: generations only, n=1, no streaming. gif: no streaming or output_compression. "
            "Both may require preview access for the OpenAI organization."
        ),
    ),
    "complexity": _enum(
        ["low", "medium", "high"],
        "high",
        "Planning effort before rendering, independent of quality; no separate fee. Lower suits focused edits, "
        "higher suits dense text and complex layouts.",
    ),
    "frame_count": _range(2, 16, 9, "GIF output only."),
    "frame_duration_ms": _range(20, 2000, 200, "GIF output only; rounded to 10 ms."),
}
_GPT_IMAGE_2_5 = _family(
    quality=["auto", "low", "medium", "high", "xhigh", "max"],
    formats=["png", "jpeg", "webp"],
    size=_CUSTOM_SIZE + " Above 2560x1440 is experimental.",
    background=_TRANSPARENT,
)
_GPT_IMAGE_2 = _family(
    quality=["auto", "low", "medium", "high"],
    formats=["png", "jpeg", "webp"],
    size=_CUSTOM_SIZE + " Above 2560x1440 is experimental; at most 3840x2160.",
    background=_TRANSPARENT + " Transparency is in preview for this model.",
)

_SNAPSHOT = r"(-\d{4}-\d{2}-\d{2})?"
_OPENAI_FAMILIES: list[tuple[re.Pattern[str], dict[str, ImageParameter]]] = [
    (re.compile(r"gpt-image-2\.6-(sunburst|flare)" + _SNAPSHOT), _GPT_IMAGE_2_6),
    (re.compile(r"gpt-image-2\.5-(sunburst|flare)" + _SNAPSHOT), _GPT_IMAGE_2_5),
    (re.compile(r"gpt-image-2" + _SNAPSHOT), _GPT_IMAGE_2),
]

# The native ChatGPT image endpoint documents nothing; these are the values the Codex client sends to it.
_NATIVE_GPT_IMAGE_2 = {
    "background": _enum(["opaque", "transparent"]),
    "quality": _enum(["auto"], "auto"),
    "size": _enum(["auto"], "auto"),
}


def _published(parameters: dict[str, ImageParameter]) -> dict[str, JsonValue]:
    return {name: parameter.model_dump(mode="json", exclude_defaults=True) for name, parameter in parameters.items()}


def native_image_description(model: str) -> dict[str, JsonValue]:
    return {"id": model, "supported_parameters": _published(_NATIVE_GPT_IMAGE_2)}


def published_image_description(model: UpstreamModel) -> dict[str, JsonValue]:
    """The ``image`` block of a source image model on ``/v1/models``."""
    image = model.raw["image"]
    assert isinstance(image, dict)
    if model.source_kind != "openai_apikey":
        return image
    upstream = image["id"]
    assert isinstance(upstream, str)
    for pattern, parameters in _OPENAI_FAMILIES:
        if pattern.fullmatch(upstream):
            return {**image, "supported_parameters": _published(parameters)}
    return image
