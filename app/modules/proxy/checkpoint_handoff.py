"""On-demand native-to-source handoff; never an archive of native input.

Records are addressed by API key and checkpoint digest. The digest names a
ciphertext only that key's client history carries, so forked conversations,
which replay the same checkpoint under a new conversation ID, share them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import anyio

from app.core.clients.proxy import ProxyResponseError
from app.core.clock import REAL_CLOCK, REAL_SCHEDULER, Clock, Scheduler
from app.core.config.settings import get_settings
from app.core.errors import openai_error
from app.core.openai.compaction import encode_codex_lb_compaction_summary, project_source_compaction_item
from app.core.types import JsonValue
from app.core.utils.request_id import get_request_id
from app.core.utils.shared_future import _await_cleanup_deferring_cancellation, _await_result_deferring_cancellation
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_sources.compaction import (
    SourceCompactionResultError,
    extract_completed_source_compaction_summary,
)
from app.modules.proxy.replay_store import ApiKeyScope, HTTPFallbackReplayStore
from app.modules.proxy.request_policy import validate_model_access

logger = logging.getLogger(__name__)
RETENTION_SECONDS = 30 * 24 * 3600
HANDOFF_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class NativeCheckpointOrigin:
    model: str
    account_id: str
    item: dict[str, JsonValue]


type HandoffGenerator = Callable[[NativeCheckpointOrigin, dict[str, JsonValue]], Awaitable[dict[str, JsonValue]]]
type CheckpointResolver = Callable[[ApiKeyScope, dict[str, JsonValue]], Awaitable[list[JsonValue] | None]]


def checkpoint_digest(ciphertext: str) -> str:
    return "checkpoint:" + hashlib.sha256(ciphertext.encode()).hexdigest()


def origin_store() -> HTTPFallbackReplayStore:
    return HTTPFallbackReplayStore(
        get_settings().data_dir / "checkpoint-origins",
        ttl_seconds=RETENTION_SECONDS,
        max_entries=10_000,
        max_entry_bytes=32 * 1024,
        max_total_bytes=16 * 1024 * 1024,
    )


def handoff_store() -> HTTPFallbackReplayStore:
    return HTTPFallbackReplayStore(
        get_settings().data_dir / "checkpoint-handoffs",
        ttl_seconds=RETENTION_SECONDS,
        max_entry_bytes=512 * 1024,
        max_total_bytes=64 * 1024 * 1024,
    )


async def remember_checkpoint_origin(
    scope: ApiKeyScope | None, model: str, account_id: str, item: dict[str, JsonValue]
) -> None:
    ciphertext = item.get("encrypted_content")
    if scope is None or not isinstance(ciphertext, str):
        return
    # Native item metadata is needed to replay the exact upstream-issued item.
    # Conversation input and ciphertext never enter this record.
    metadata = {key: value for key, value in item.items() if key != "encrypted_content"}
    await origin_store().remember(
        scope, checkpoint_digest(ciphertext), json.dumps({"model": model, "input": []}), [metadata], account_id
    )


class HandoffClaims:
    """Short-lived cross-worker claims; no network await holds a DB transaction."""

    def __init__(self, directory: Path, *, clock: Clock = REAL_CLOCK, scheduler: Scheduler = REAL_SCHEDULER) -> None:
        self.directory = directory
        self.clock = clock
        self.scheduler = scheduler

    def _change(self, key: str, token: str, *, release: bool) -> bool:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.directory / "generation-claims.sqlite"
        os.close(os.open(path, os.O_CREAT | os.O_RDWR, 0o600))
        with sqlite3.connect(path, timeout=5) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS claims (key TEXT PRIMARY KEY, token TEXT, expires REAL)")
            connection.execute("BEGIN IMMEDIATE")
            now = self.clock.time()
            connection.execute("DELETE FROM claims WHERE expires <= ?", (now,))
            if release:
                connection.execute("DELETE FROM claims WHERE key = ? AND token = ?", (key, token))
                return True
            cursor = connection.execute(
                "INSERT OR IGNORE INTO claims VALUES (?, ?, ?)",
                (key, token, now + HANDOFF_TIMEOUT_SECONDS + 30),
            )
            return cursor.rowcount == 1

    async def acquire(self, scope: ApiKeyScope, digest: str) -> tuple[str, str] | None:
        key = hashlib.sha256(json.dumps([scope.api_key_id, digest]).encode()).hexdigest()
        token = uuid4().hex
        try:
            acquired, cancellation = await _await_result_deferring_cancellation(
                anyio.to_thread.run_sync(lambda: self._change(key, token, release=False)), scheduler=self.scheduler
            )
            if cancellation is not None:
                if acquired:
                    await self.release((key, token))
                raise cancellation
            if acquired:
                return key, token
        except (OSError, sqlite3.Error) as exc:
            raise ProxyResponseError(
                503, openai_error("compaction_handoff_unavailable", "Checkpoint handoff coordination is unavailable.")
            ) from exc
        return None

    async def release(self, claim: tuple[str, str]) -> None:
        try:
            cancellation = await _await_cleanup_deferring_cancellation(
                anyio.to_thread.run_sync(lambda: self._change(*claim, release=True)), scheduler=self.scheduler
            )
            if cancellation is not None:
                raise cancellation
        except (OSError, sqlite3.Error):
            # The deadline still releases a stranded claim. Cleanup failure
            # must not obscure generation failure or an already settled result.
            logger.warning("compaction_handoff_claim_release_failed request_id=%s", get_request_id())


class CheckpointHandoff:
    def __init__(self, api_key: ApiKeyData | None, generate: HandoffGenerator) -> None:
        self.api_key = api_key
        self.generate = generate

    def _validate_access(self, scope: ApiKeyScope, model: str, account_id: str) -> None:
        validate_model_access(self.api_key, model)
        if (
            self.api_key is None
            or self.api_key.id != scope.api_key_id
            or (self.api_key.account_assignment_scope_enabled and account_id not in self.api_key.assigned_account_ids)
        ):
            raise ProxyResponseError(
                403,
                openai_error(
                    "compaction_handoff_forbidden", "The original checkpoint account is outside this key's scope."
                ),
            )

    async def resolve(self, scope: ApiKeyScope, item: dict[str, JsonValue]) -> list[JsonValue] | None:
        ciphertext = item["encrypted_content"]
        assert isinstance(ciphertext, str)
        digest = checkpoint_digest(ciphertext)
        summaries = handoff_store()
        cached = await summaries.load(scope, digest)
        if cached is not None:
            self._validate_access(scope, cached.model, cached.account_id)
            return cached.input
        provenance = await origin_store().load(scope, digest)
        if provenance is None or len(provenance.output) != 1 or not isinstance(provenance.output[0], dict):
            return None
        origin = NativeCheckpointOrigin(provenance.model, provenance.account_id, provenance.output[0])
        self._validate_access(scope, origin.model, origin.account_id)
        claims = HandoffClaims(summaries.directory)
        claim = await claims.acquire(scope, digest)
        if claim is None:
            raise ProxyResponseError(
                503,
                openai_error("compaction_handoff_in_progress", "Checkpoint handoff is in progress; retry shortly."),
                retry_after_header="2",
                retry_after_seconds=2,
            )
        try:
            # Another worker can publish between our initial lookup and claim.
            cached = await summaries.load(scope, digest)
            if cached is not None:
                self._validate_access(scope, cached.model, cached.account_id)
                return cached.input
            logger.info("compaction_handoff_started request_id=%s", get_request_id())
            result = await self.generate(origin, {**origin.item, "encrypted_content": ciphertext})
            try:
                summary = extract_completed_source_compaction_summary(result)
            except SourceCompactionResultError as exc:
                raise ProxyResponseError(
                    502, openai_error("compaction_handoff_invalid", str(exc), error_type="upstream_error")
                ) from exc
            output = result["output"]
            assert isinstance(output, list)  # Validated by the summary extractor.
            for message in output:
                assert isinstance(message, dict)  # Only message/reasoning items pass the extractor.
                content = message.get("content")
                if isinstance(content, list) and any(
                    isinstance(part, dict) and part.get("type") == "refusal" for part in content
                ):
                    raise ProxyResponseError(
                        502, openai_error("compaction_handoff_invalid", "Native handoff was refused.")
                    )
            projected = project_source_compaction_item(
                {"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary(summary)}, 0
            )
            assert projected is not None
            items: list[JsonValue] = [projected]
            await summaries.remember(
                scope, digest, json.dumps({"model": origin.model, "input": items}), [], origin.account_id
            )
            cached = await summaries.load(scope, digest)
            if cached is None:
                raise ProxyResponseError(
                    503, openai_error("compaction_handoff_not_retained", "Handoff summary could not be retained.")
                )
            logger.info("compaction_handoff_completed request_id=%s", get_request_id())
            return items
        finally:
            await claims.release(claim)
