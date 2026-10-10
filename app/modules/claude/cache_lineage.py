"""Names the prompt part that changed when a Claude request misses the cache.

Claude caches a byte-exact prefix: tools, then system, then messages. A request
that reads nothing yet writes a large prefix means something early in that
prefix differs from the request that warmed it. Each conversation's latest
request is remembered as digests only, and a full miss is compared with it or,
for a forked side chat, with its parent session's latest request.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue

from app.core.clock import REAL_CLOCK, Clock

logger = logging.getLogger(__name__)

_UNCACHED_PARAMS = frozenset({"messages", "tools", "system", "metadata", "stream", "max_tokens"})
_LISTED_NAMES = 8
_CAPACITY = 256


def _without_markers(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {key: _without_markers(item) for key, item in value.items() if key != "cache_control"}
    if isinstance(value, list):
        return [_without_markers(item) for item in value]
    return value


def _digest(value: JsonValue) -> str:
    encoded = json.dumps(_without_markers(value), ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.blake2b(encoded, digest_size=8).hexdigest()


def _names(names: list[str]) -> str:
    listed = ",".join(names[:_LISTED_NAMES])
    return listed if len(names) <= _LISTED_NAMES else f"{listed},(+{len(names) - _LISTED_NAMES})"


@dataclass(frozen=True, slots=True)
class PrefixShape:
    source_id: str
    observed_at: float
    tools: tuple[tuple[str, str], ...]
    system: str
    params: tuple[tuple[str, str], ...]
    messages: tuple[str, ...]

    @classmethod
    def of(cls, body: dict[str, JsonValue], *, source_id: str, observed_at: float) -> PrefixShape:
        tools = body.get("tools")
        messages = body.get("messages")
        return cls(
            source_id=source_id,
            observed_at=observed_at,
            tools=tuple(
                (str(tool.get("name") or tool.get("type")), _digest(tool))
                for tool in (tools if isinstance(tools, list) else [])
                if isinstance(tool, dict)
            ),
            system=_digest(body.get("system")),
            params=tuple((key, _digest(value)) for key, value in body.items() if key not in _UNCACHED_PARAMS),
            messages=tuple(
                _digest({"role": message.get("role"), "content": message.get("content")})
                for message in (messages if isinstance(messages, list) else [])
                if isinstance(message, dict)
            ),
        )


def _tool_change(reference: PrefixShape, current: PrefixShape) -> str:
    before = dict(reference.tools)
    after = dict(current.tools)
    added = [name for name in after if name not in before]
    removed = [name for name in before if name not in after]
    changed = [name for name, digest in after.items() if name in before and before[name] != digest]
    parts = [
        f"{label}:{_names(names)}"
        for label, names in (("added", added), ("removed", removed), ("changed", changed))
        if names
    ]
    if parts:
        return ";".join(parts)
    return "same" if reference.tools == current.tools else "reordered"


def _param_change(reference: PrefixShape, current: PrefixShape) -> str:
    before = dict(reference.params)
    after = dict(current.params)
    keys = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
    return f"changed({_names(keys)})" if keys else "same"


def _message_blocks(message: JsonValue) -> str:
    if not isinstance(message, dict):
        return "?"
    content = message.get("content")
    if isinstance(content, str):
        kinds = "text"
    elif isinstance(content, list):
        kinds = ",".join(str(block.get("type")) if isinstance(block, dict) else "?" for block in content)
    else:
        kinds = ""
    return f"{message.get('role')}[{kinds}]"


class CacheLineage:
    def __init__(self, *, capacity: int = _CAPACITY, clock: Clock = REAL_CLOCK) -> None:
        self._capacity = capacity
        self._clock = clock
        self._shapes: OrderedDict[str, PrefixShape] = OrderedDict()

    def observe(
        self,
        *,
        conversation_id: str,
        session_id: str | None,
        source_id: str,
        body: dict[str, JsonValue],
        usage: object,
    ) -> None:
        current = PrefixShape.of(body, source_id=source_id, observed_at=self._clock.monotonic())
        if conversation_id in self._shapes:
            relation, reference_id = "self", conversation_id
        else:
            relation, reference_id = "parent", session_id
        reference = self._shapes.get(reference_id) if reference_id else None
        written = _full_miss_write(usage)
        if reference is not None and written is not None:
            self._log(conversation_id, relation, reference_id, reference, current, body, written)
        self._shapes[conversation_id] = current
        self._shapes.move_to_end(conversation_id)
        while len(self._shapes) > self._capacity:
            self._shapes.popitem(last=False)

    def _log(
        self,
        conversation_id: str,
        relation: str,
        reference_id: str | None,
        reference: PrefixShape,
        current: PrefixShape,
        body: dict[str, JsonValue],
        written: int,
    ) -> None:
        divergence = next(
            (index for index, (a, b) in enumerate(zip(reference.messages, current.messages)) if a != b),
            None,
        )
        messages = body.get("messages")
        divergent = (
            _message_blocks(messages[divergence]) if divergence is not None and isinstance(messages, list) else "-"
        )
        logger.info(
            "claude_cache_miss conversation_id=%s reference=%s reference_id=%s same_source=%s idle_s=%.0f "
            "cache_write=%s tools=%s system=%s params=%s messages=%d/%d first_divergence=%s divergent_message=%s",
            conversation_id,
            relation,
            reference_id,
            reference.source_id == current.source_id,
            current.observed_at - reference.observed_at,
            written,
            _tool_change(reference, current),
            "same" if reference.system == current.system else "changed",
            _param_change(reference, current),
            len(reference.messages),
            len(current.messages),
            "none" if divergence is None else divergence,
            divergent,
        )


def _full_miss_write(usage: object) -> int | None:
    """Tokens written by a request that read nothing from the cache."""
    if not isinstance(usage, Mapping):
        return None
    written = usage.get("cache_creation_input_tokens")
    if usage.get("cache_read_input_tokens") == 0 and isinstance(written, int) and written > 0:
        return written
    return None


CACHE_LINEAGE = CacheLineage()
