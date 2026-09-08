"""Private, bounded continuation storage for stateless HTTP fallback turns.

Port of OpenCodex's input-plus-output retention and identity-checked full resend
rules (state.ts at 9a27e86992d7a014e0aa92c046199b9fac148201). Small serialized
entries stay resident; large histories spill to disk. Atomic files also persist
resident entries for restart recovery. SQLite's process lock serializes file
publication across workers without depending on Unix-only flock.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, cast

import anyio

from app.core.clock import REAL_CLOCK, Clock
from app.core.types import JsonValue

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReplayScope:
    api_key_id: str | None
    conversation_id: str


@dataclass(frozen=True)
class ReplayHistory:
    account_id: str
    model: str
    input: list[JsonValue]
    output: list[JsonValue]

    def expand(self, delta: list[JsonValue]) -> list[JsonValue]:
        history = [*self.input, *self.output]
        # Content equality alone does not distinguish a repeated user message
        # from a full resend. Require an upstream-issued output identity too.
        if (
            any(
                isinstance(item, dict)
                and any(isinstance(value := item.get(key), str) and value.strip() for key in ("id", "call_id"))
                for item in self.output
            )
            and delta[: len(history)] == history
        ):
            return delta
        return [*history, *delta]


class HTTPFallbackReplayStore:
    def __init__(
        self,
        directory: Path,
        *,
        ttl_seconds: float = 3600,
        max_entries: int = 1000,
        max_entry_bytes: int = 256 * 1024 * 1024,
        max_total_bytes: int = 1024 * 1024 * 1024,
        max_memory_bytes: int = 64 * 1024 * 1024,
        clock: Clock = REAL_CLOCK,
    ) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self.max_total_bytes = max_total_bytes
        self.max_memory_bytes = max_memory_bytes
        self._clock = clock
        self._resident: OrderedDict[Path, tuple[int, bytes]] = OrderedDict()
        self._limiter = anyio.CapacityLimiter(1)

    def _path(self, scope: ReplayScope, response_id: str) -> Path:
        key = json.dumps([scope.api_key_id, scope.conversation_id, response_id]).encode()
        return self.directory / (hashlib.sha256(key).hexdigest() + ".replay")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = self.directory / "cache.lock"
        os.close(os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600))
        connection = sqlite3.connect(lock_path, timeout=5)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield
        finally:
            connection.close()

    def _retain(self, path: Path, stamp: int, body: bytes) -> None:
        self._resident.pop(path, None)
        if len(body) > self.max_memory_bytes:
            return
        self._resident[path] = (stamp, body)
        total = sum(len(value) for _, value in self._resident.values())
        while total > self.max_memory_bytes:
            _, (_, removed) = self._resident.popitem(last=False)
            total -= len(removed)

    def _prune(self, *, incoming_bytes: int = 0) -> None:
        entries: list[tuple[float, Path, int]] = []
        cutoff = self._clock.time() - self.ttl_seconds
        for path in self.directory.iterdir():
            if path.suffix not in {".replay", ".tmp"}:
                continue
            stat = path.stat()
            # No writer can be active while we hold the lock: tmp files are
            # leftovers of interrupted publication, never live entries.
            if path.suffix == ".tmp" or stat.st_mtime <= cutoff:
                path.unlink()
                self._resident.pop(path, None)
            else:
                entries.append((stat.st_mtime, path, stat.st_size))
        entries.sort()
        live_paths = {path for _, path, _ in entries}
        for path in list(self._resident):
            if path not in live_paths:
                self._resident.pop(path)
        total = sum(size for _, _, size in entries) + incoming_bytes
        count = len(entries) + bool(incoming_bytes)
        for _, path, size in entries:
            if count <= self.max_entries and total <= self.max_total_bytes:
                break
            path.unlink()
            self._resident.pop(path, None)
            count -= 1
            total -= size

    async def load(self, scope: ReplayScope, response_id: str) -> ReplayHistory | None:
        try:
            return await anyio.to_thread.run_sync(self._load, scope, response_id, limiter=self._limiter)
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            logger.warning("http_fallback_replay_unavailable")
            return None

    def _load(self, scope: ReplayScope, response_id: str) -> ReplayHistory | None:
        with self._locked():
            self._prune()
            path = self._path(scope, response_id)
            if not path.exists():
                self._resident.pop(path, None)
                return None
            if path.stat().st_size > self.max_entry_bytes:
                path.unlink()
                self._resident.pop(path, None)
                return None
            stamp = path.stat().st_mtime_ns
            resident = self._resident.get(path)
            serialized = resident[1] if resident is not None and resident[0] == stamp else path.read_bytes()
            digest, separator, content = serialized.partition(b"\n")
            if not separator or digest != hashlib.sha256(content).hexdigest().encode():
                self._resident.pop(path, None)
                raise ValueError("Replay digest mismatch")
            self._retain(path, stamp, serialized)
            body = json.loads(content)
            if (
                not isinstance(body, dict)
                or not isinstance(body.get("account_id"), str)
                or not isinstance(body.get("model"), str)
                or not isinstance(body.get("input"), list)
                or not isinstance(body.get("output"), list)
            ):
                raise ValueError("Invalid replay entry")
            return ReplayHistory(body["account_id"], body["model"], body["input"], body["output"])

    async def remember(
        self,
        scope: ReplayScope,
        response_id: str,
        request_text: str,
        output: list[JsonValue],
        account_id: str,
        original_input: JsonValue = None,
    ) -> None:
        try:
            await anyio.to_thread.run_sync(
                self._remember,
                scope,
                response_id,
                request_text,
                output,
                account_id,
                original_input,
                limiter=self._limiter,
            )
        except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
            # A completed model response must still settle and reach the client.
            # The next turn uses the explicit cache-miss recovery path.
            logger.warning("http_fallback_replay_not_retained")

    def _remember(
        self,
        scope: ReplayScope,
        response_id: str,
        request_text: str,
        output: list[JsonValue],
        account_id: str,
        original_input: JsonValue,
    ) -> None:
        request = json.loads(request_text)
        if request.get("previous_response_id"):
            return
        input_value = original_input if original_input is not None else request.get("input", [])
        if isinstance(input_value, str):
            input_value = [{"role": "user", "content": input_value}]
        body = json.dumps(
            {
                "account_id": account_id,
                "model": request["model"],
                "input": cast(list[JsonValue], input_value),
                "output": output,
            },
            separators=(",", ":"),
        ).encode()
        body = hashlib.sha256(body).hexdigest().encode() + b"\n" + body
        if len(body) > min(self.max_entry_bytes, self.max_total_bytes):
            logger.warning("http_fallback_replay_entry_too_large bytes=%d", len(body))
            return
        with self._locked():
            path = self._path(scope, response_id)
            path.unlink(missing_ok=True)
            self._prune(incoming_bytes=len(body))
            fd, name = tempfile.mkstemp(suffix=".tmp", dir=self.directory)
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(path)
                completed_at = self._clock.time()
                os.utime(path, (completed_at, completed_at))
                self._retain(path, path.stat().st_mtime_ns, body)
            finally:
                temporary.unlink(missing_ok=True)

    async def sweep(self) -> None:
        try:
            await anyio.to_thread.run_sync(self._sweep, limiter=self._limiter)
        except (OSError, sqlite3.Error):
            logger.warning("http_fallback_replay_cleanup_failed")

    def _sweep(self) -> None:
        if self.directory.exists():
            with self._locked():
                self._prune()
