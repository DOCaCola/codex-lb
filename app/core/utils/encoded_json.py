"""JSON objects that keep the encoded text of their top-level members.

A body that is already serialized (an upstream ``response.create`` frame) can
be parsed once into an :class:`EncodedJsonObject`. When a rewritten copy of it
is serialized again, every top-level member whose value is still identical
reuses its original text, so only the members that actually changed are
encoded. For an image-heavy frame that skips re-encoding tens of megabytes of
history that no rewrite touched.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.core.types import JsonValue

_DECODER = json.JSONDecoder()
_WHITESPACE = re.compile(r"[ \t\n\r]*")


@dataclass(frozen=True, slots=True)
class EncodedJsonObject:
    """A parsed JSON object and the source text of each top-level member value."""

    values: dict[str, JsonValue]
    encoded: dict[str, str]


def decode_json_object(text: str) -> EncodedJsonObject:
    """Parse a JSON object in one pass, recording each member's encoded value.

    Accepts and rejects exactly what ``json.loads`` does for an object, raising
    ``json.JSONDecodeError`` otherwise. A repeated key keeps its last value, as
    ``json.loads`` does.
    """
    values: dict[str, JsonValue] = {}
    encoded: dict[str, str] = {}
    index = _skip_whitespace(text, 0)
    if text[index : index + 1] != "{":
        raise json.JSONDecodeError("Expecting JSON object", text, index)
    index = _skip_whitespace(text, index + 1)
    if text[index : index + 1] == "}":
        index += 1
    else:
        while True:
            if text[index : index + 1] != '"':
                raise json.JSONDecodeError("Expecting property name enclosed in double quotes", text, index)
            key, index = _DECODER.raw_decode(text, index)
            index = _skip_whitespace(text, index)
            if text[index : index + 1] != ":":
                raise json.JSONDecodeError("Expecting ':' delimiter", text, index)
            start = _skip_whitespace(text, index + 1)
            value, end = _DECODER.raw_decode(text, start)
            values[key] = value
            encoded[key] = text[start:end]
            index = _skip_whitespace(text, end)
            delimiter = text[index : index + 1]
            index += 1
            if delimiter == "}":
                break
            if delimiter != ",":
                raise json.JSONDecodeError("Expecting ',' delimiter", text, index - 1)
            index = _skip_whitespace(text, index)
    end = _skip_whitespace(text, index)
    if end != len(text):
        raise json.JSONDecodeError("Extra data", text, end)
    return EncodedJsonObject(values=values, encoded=encoded)


def _skip_whitespace(text: str, index: int) -> int:
    match = _WHITESPACE.match(text, index)
    # The pattern accepts the empty string, so it matches at every index.
    assert match is not None
    return match.end()


def encode_json_object(payload: Mapping[str, JsonValue], source: EncodedJsonObject | None = None) -> str:
    """Serialize ``payload`` compactly, reusing ``source`` text for unchanged members.

    A member reuses its source text only when its value is structurally
    identical to the parsed source value, with JSON types kept distinct
    (``true`` is not ``1``). Every other member is encoded as ``json.dumps``
    would encode it with ``ensure_ascii=True`` and compact separators.
    """
    if source is None:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    # One flat join: a large reused member is copied once, into the result.
    parts: list[str] = ["{"]
    for key, value in payload.items():
        encoded = source.encoded.get(key)
        if encoded is None or not _json_identical(value, source.values[key]):
            encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        if len(parts) > 1:
            parts.append(",")
        parts.extend((json.dumps(key, ensure_ascii=True), ":", encoded))
    parts.append("}")
    return "".join(parts)


def _json_identical(left: JsonValue, right: JsonValue) -> bool:
    if left is right:
        return True
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        assert isinstance(right, dict)
        return left.keys() == right.keys() and all(_json_identical(item, right[key]) for key, item in left.items())
    if isinstance(left, list):
        assert isinstance(right, list)
        return len(left) == len(right) and all(map(_json_identical, left, right))
    return left == right
