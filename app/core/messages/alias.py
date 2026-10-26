"""Model aliases that keep Responses models in Claude Code's discovered model picker.

Claude Code keeps a discovered model only when its ID contains `claude` or `anthropic`, and treats
an unknown ID starting with `claude-` as an Anthropic model whose context window it fixes. The
alias therefore contains `claude` without starting with `claude-` (opencodex `ocx-claude-`).
Slashes and tildes are escaped so the alias is slash-free and decodes unambiguously.

Claude Code can only choose a model, so Fast Mode for a Responses model is a sibling alias ending in
`~fast` (opencodex `--fast` rows). A tilde in a model name is always escaped, so the marker never
collides with a real model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.core.messages.errors import MessagesRequestError

MODEL_ALIAS_PREFIX: Final = "clb-claude-"
FAST_SELECTOR_SUFFIX: Final = "~fast"


@dataclass(frozen=True, slots=True)
class ModelSelection:
    model: str
    fast: bool = False


def discovery_alias(model: str, *, fast: bool = False) -> str:
    alias = MODEL_ALIAS_PREFIX + model.replace("~", "~t").replace("/", "~s")
    return alias + FAST_SELECTOR_SUFFIX if fast else alias


def decode_discovery_alias(model: str) -> ModelSelection:
    """The model and Fast selection an alias names; any other model name is returned unchanged."""
    if not model.startswith(MODEL_ALIAS_PREFIX):
        return ModelSelection(model)
    encoded = model[len(MODEL_ALIAS_PREFIX) :]
    fast = encoded.endswith(FAST_SELECTOR_SUFFIX)
    if fast:
        encoded = encoded[: -len(FAST_SELECTOR_SUFFIX)]
    decoded: list[str] = []
    index = 0
    while index < len(encoded):
        char = encoded[index]
        if char != "~":
            decoded.append(char)
            index += 1
            continue
        escape = encoded[index + 1 : index + 2]
        if escape not in ("s", "t"):
            raise MessagesRequestError(f"Model alias '{model}' is not valid")
        decoded.append("/" if escape == "s" else "~")
        index += 2
    if not decoded:
        raise MessagesRequestError(f"Model alias '{model}' is not valid")
    return ModelSelection("".join(decoded), fast)
