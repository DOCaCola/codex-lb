"""Native Messages metering without rewriting provider content or tool blocks."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.core.types import JsonValue
from app.core.utils.sse import format_sse_event, parse_sse_data_json
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.responses import Usage
from app.modules.model_sources.forwarding import ModelSourceForwardingError, SourceUsage, SourceUsageHolder


def usage_totals(usage: Usage) -> SourceUsage:
    return SourceUsage(
        input_tokens=usage.input_tokens + usage.cache_read_input_tokens + usage.cache_creation_input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=usage.cache_read_input_tokens,
    )


@dataclass
class NativeObserver:
    holder: SourceUsageHolder
    usage: Usage = field(default_factory=Usage)
    started: bool = False
    stopped: bool = False
    stop_reason: str | None = None
    open_blocks: set[int] = field(default_factory=set)
    seen_blocks: set[int] = field(default_factory=set)

    def consume(self, event: dict[str, JsonValue]) -> None:
        kind = event.get("type")
        if self.stopped:
            raise ClaudeError("Claude emitted events after message_stop")
        if kind == "message_start":
            message = event.get("message")
            if self.started or not isinstance(message, dict):
                raise ClaudeError("Invalid Claude message_start")
            self.started = True
            response_id = message.get("id")
            self.holder.response_id = response_id if isinstance(response_id, str) else None
            self.usage = Usage.model_validate(message.get("usage", {}))
        elif kind == "message_delta":
            delta = event.get("delta")
            if not self.started or not isinstance(delta, dict):
                raise ClaudeError("Invalid Claude message_delta")
            reason = delta.get("stop_reason")
            self.stop_reason = reason if isinstance(reason, str) else None
            update = event.get("usage", {})
            if not isinstance(update, dict):
                raise ClaudeError("Invalid Claude usage delta")
            self.usage = Usage.model_validate({**self.usage.model_dump(), **update})
        elif kind == "message_stop":
            if not self.started or self.stop_reason is None or self.open_blocks:
                raise ClaudeError("Claude ended before a stop reason")
            self.stopped = True
            self.holder.terminal_kind = (
                "incomplete" if self.stop_reason in ("pause_turn", "max_tokens") else "completed"
            )
            self.holder.successful_terminal_seen = True
        elif kind == "error":
            self.stopped = True
            self.holder.terminal_kind = "error"
        elif kind in ("content_block_start", "content_block_delta", "content_block_stop"):
            if not self.started:
                raise ClaudeError("Claude content preceded message_start")
            index = event.get("index")
            if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                raise ClaudeError("Invalid native Claude content index")
            if kind == "content_block_start":
                if index in self.seen_blocks:
                    raise ClaudeError("Duplicate native Claude content block")
                self.seen_blocks.add(index)
                self.open_blocks.add(index)
            elif index not in self.open_blocks:
                raise ClaudeError("Native Claude event refers to an unopened content block")
            elif kind == "content_block_stop":
                self.open_blocks.remove(index)
            self.holder.first_content_seen = True
        if self.started:
            self.holder.usage = usage_totals(self.usage)


def terminal_kind(frame: str | None) -> str | None:
    event = parse_sse_data_json(frame) if frame else None
    if event is None:
        return None
    return {"message_stop": "completed", "error": "error"}.get(str(event.get("type")))


def delivers_content(frame: str | None) -> bool:
    event = parse_sse_data_json(frame) if frame else None
    return event is not None and event.get("type") in {
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_stop",
    }


async def native_frames(body: AsyncIterator[bytes]) -> AsyncIterator[str]:
    async for frame in body:
        yield frame.decode("utf-8")


async def native_error_stream(body: AsyncIterator[str]) -> AsyncIterator[str]:
    """Serialize gateway failures after settlement has recorded the original cause."""
    try:
        async for frame in body:
            yield frame
    except ModelSourceForwardingError as exc:
        error = exc.payload.get("error")
        message = error.get("message") if isinstance(error, dict) else None
        yield format_sse_event(
            {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": message if isinstance(message, str) else "Claude upstream stream failed",
                },
            }
        )
