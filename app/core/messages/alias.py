"""Model aliases that keep Responses models in Claude Code's discovered model picker.

Claude Code keeps a discovered model only when its ID contains `claude` or `anthropic`, and treats
an unknown ID starting with `claude-` as an Anthropic model whose context window it fixes. The
alias therefore contains `claude` without starting with `claude-` (opencodex `ocx-claude-`).
Slashes and tildes are escaped so the alias is slash-free and decodes unambiguously.
"""

from __future__ import annotations

from typing import Final

from app.core.messages.errors import MessagesRequestError

MODEL_ALIAS_PREFIX: Final = "clb-claude-"


def discovery_alias(model: str) -> str:
    return MODEL_ALIAS_PREFIX + model.replace("~", "~t").replace("/", "~s")


def decode_discovery_alias(model: str) -> str:
    """The model an alias names; any other model name is returned unchanged."""
    if not model.startswith(MODEL_ALIAS_PREFIX):
        return model
    encoded = model[len(MODEL_ALIAS_PREFIX) :]
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
    return "".join(decoded)
