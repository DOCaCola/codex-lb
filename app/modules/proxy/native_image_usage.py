from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from app.core.clients.proxy import CodexControlResponse

# One SSE event is retained only until its terminating blank line. Partial
# images make events large, so the bound matches the buffered-response limit.
_MAX_EVENT_BYTES = 100 * 1024 * 1024


class NativeImageInputUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    cached_tokens: int | None = Field(default=None, ge=0)


class NativeImageUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    input_tokens_details: NativeImageInputUsage | None = None

    @property
    def cached_input_tokens(self) -> int | None:
        return self.input_tokens_details.cached_tokens if self.input_tokens_details is not None else None


def reported_image_usage(response: CodexControlResponse) -> NativeImageUsage:
    if not 200 <= response.status_code < 300:
        return NativeImageUsage()
    try:
        body = json.loads(response.body)
        if isinstance(body, dict):
            return _usage_from_payload(body)
    except (ValueError, UnicodeDecodeError):
        pass
    # Missing or unreadable usage is not evidence of token consumption.
    return NativeImageUsage()


def _usage_from_payload(payload: Mapping[str, object]) -> NativeImageUsage:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return NativeImageUsage()
    try:
        return NativeImageUsage.model_validate(usage)
    except ValueError:
        return NativeImageUsage()


@dataclass
class NativeImageAccounting:
    """One request-owned usage snapshot for logging and quota settlement."""

    model: str
    usage: NativeImageUsage = field(default_factory=NativeImageUsage)
    # Set once a native event stream ends: success, image_error or
    # stream_incomplete. Buffered responses leave it unset.
    stream_outcome: str | None = None

    def capture(self, response: CodexControlResponse) -> None:
        self.usage = reported_image_usage(response)

    def capture_completed_event(self, event: Mapping[str, object]) -> None:
        self.usage = _usage_from_payload(event)


class NativeImageStreamObserver:
    """Read native Images API SSE incrementally for usage and terminal state.

    Chunks are forwarded unchanged by the caller; the observer only keeps the
    bytes of the event that is still open.
    """

    def __init__(self, accounting: NativeImageAccounting) -> None:
        self._accounting = accounting
        self._pending = bytearray()
        self._scan_from = 0
        self._overflowed = False
        self.completed = False
        self.error: dict[str, object] | None = None

    @property
    def at_event_boundary(self) -> bool:
        return not self._overflowed and not self._pending.strip()

    def feed(self, chunk: bytes) -> None:
        if self._overflowed:
            return
        self._pending.extend(chunk)
        while True:
            end, separator = self._next_boundary()
            if end < 0:
                break
            block = bytes(self._pending[:end])
            del self._pending[: end + separator]
            self._scan_from = 0
            self._observe(block)
        # A separator may straddle chunks; rescan its possible prefix.
        self._scan_from = max(0, len(self._pending) - 3)
        if len(self._pending) > _MAX_EVENT_BYTES:
            self._overflowed = True
            self._pending.clear()

    def _next_boundary(self) -> tuple[int, int]:
        candidates = [
            (index, len(separator))
            for separator in (b"\n\n", b"\r\n\r\n")
            if (index := self._pending.find(separator, self._scan_from)) >= 0
        ]
        return min(candidates) if candidates else (-1, 0)

    def _observe(self, block: bytes) -> None:
        event_name: str | None = None
        data_lines: list[bytes] = []
        for line in block.splitlines():
            if line.startswith(b"event:"):
                event_name = line[6:].strip().decode("utf-8", errors="replace")
            elif line.startswith(b"data:"):
                data_lines.append(line[5:].removeprefix(b" "))
        if not data_lines:
            return
        # Partial-image events carry most of the stream's bytes and nothing
        # that accounting needs; skip decoding them when the name says so.
        if event_name is not None and not _is_terminal_event(event_name):
            return
        try:
            payload = json.loads(b"\n".join(data_lines))
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(payload, dict):
            return
        event_type = payload.get("type")
        resolved = event_type if isinstance(event_type, str) else event_name
        if resolved is None:
            return
        if resolved == "error":
            error = payload.get("error")
            self.error = error if isinstance(error, dict) else payload
        elif resolved.endswith(".completed"):
            self.completed = True
            self._accounting.capture_completed_event(payload)


def _is_terminal_event(event_name: str) -> bool:
    return event_name == "error" or event_name.endswith(".completed")
