"""OpenAI API image models: the native JSON Images body, sent with the account's key."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import AsyncExitStack
from typing import Literal

import aiohttp
from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.clients.http import lease_model_source_session
from app.core.clock import REAL_SCHEDULER
from app.core.crypto import TokenEncryptor
from app.core.errors import openai_error
from app.core.types import JsonValue
from app.core.utils.shared_future import _await_cleanup_deferring_cancellation
from app.db.models import ModelSource
from app.db.session import detach_session_objects, get_background_session
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_sources import pooled_accounts
from app.modules.model_sources.forwarding import (
    ModelSourceForwardingError,
    SourceStreamTransport,
    SourceUsage,
    _read_error_body,
    _upstream_status_error,
)
from app.modules.model_sources.repository import ModelSourcesRepository
from app.modules.model_sources.selection import allowed_source_ids_for_api_key
from app.modules.openai_api.schemas import OPENAI_API_KIND
from app.modules.openrouter.images import OwnedImageStream

MAX_IMAGE_RESPONSE_BYTES = 100 * 1024 * 1024
_COMPLETED_EVENTS = frozenset({"image_generation.completed", "image_edit.completed"})


class _TokenDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cached_tokens: int = Field(default=0, ge=0)


class ImageUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    input_tokens_details: _TokenDetails | None = None

    def source_usage(self) -> SourceUsage:
        cached = self.input_tokens_details.cached_tokens if self.input_tokens_details else 0
        return SourceUsage(self.input_tokens, self.output_tokens, cached_input_tokens=cached)


class ImageFailure(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: str | None = None) -> None:
        self.status = status
        self.payload = openai_error(
            code, message, error_type="invalid_request_error" if status < 500 else "server_error"
        )
        self.retry_after = retry_after


async def select_image_source(model: str, api_key: ApiKeyData | None, excluded: set[str]) -> ModelSource:
    allowed = allowed_source_ids_for_api_key(api_key)
    async with get_background_session() as session:
        candidates = [
            source
            for source in await ModelSourcesRepository(session).list_enabled_sources()
            if source.kind == OPENAI_API_KIND
            and (allowed is None or source.id in allowed)
            and any(
                row.model == model and row.is_enabled and "image" in json.loads(row.raw_metadata_json or "{}")
                for row in source.models
            )
        ]
        source = await pooled_accounts.select_available(session, candidates, model, excluded=excluded)
        detach_session_objects(session)
    if source is None:
        raise ImageFailure(404, "model_not_found", "No enabled, permitted OpenAI API image model matches this request")
    remaining = await pooled_accounts.cooldown_remaining(source.id, model)
    if remaining:
        raise ImageFailure(
            429, "rate_limit_exceeded", "OpenAI API image account is cooling down; retry later.", str(remaining)
        )
    return source


def _upstream_model(source: ModelSource, model: str) -> str:
    row = next(row for row in source.models if row.model == model)
    return json.loads(row.raw_metadata_json or "{}")["upstream_model"]


async def passthrough_events(
    chunks: AsyncIterator[bytes], on_completed: Callable[[JsonValue], None]
) -> AsyncIterator[bytes]:
    """Forward the event stream byte for byte while reading usage from its completed event."""
    buffer = bytearray()
    total = 0
    async for chunk in chunks:
        total += len(chunk)
        if total > MAX_IMAGE_RESPONSE_BYTES:
            raise ImageFailure(502, "upstream_error", "OpenAI image stream exceeds the allowed size")
        buffer.extend(chunk.replace(b"\r\n", b"\n"))
        while (end := buffer.find(b"\n\n")) >= 0:
            frame = bytes(buffer[:end])
            del buffer[: end + 2]
            data = b"\n".join(line[5:].lstrip(b" ") for line in frame.split(b"\n") if line.startswith(b"data:"))
            if data and data != b"[DONE]":
                event = json.loads(data)
                if isinstance(event, dict) and event.get("type") in _COMPLETED_EVENTS:
                    on_completed(event.get("usage"))
        yield chunk


async def image_response(
    request: Request,
    body: dict[str, object],
    api_key: ApiKeyData | None,
    *,
    operation: Literal["generations", "edits"],
    model: str,
    rate_limit_headers: Mapping[str, str],
) -> Response:
    from app.modules.proxy import api

    headers = dict(rate_limit_headers)
    reservation = await api._enforce_request_limits(api_key, request_model=model, request_service_tier=None)
    source: ModelSource | None = None
    usage: SourceUsage | None = None
    completed = False
    finalized = False
    handed_off = False
    upstream_status: int | None = None
    error_code: str | None = "client_disconnected"
    error_message: str | None = "Image request ended before completion"
    stack = AsyncExitStack()
    transport = SourceStreamTransport(stack, scheduler=REAL_SCHEDULER)

    async def finish() -> None:
        nonlocal finalized
        if finalized:
            return
        finalized = True
        failure: tuple[str, str] | None = None
        try:
            if source is None or not completed:
                # Nothing was generated: no account was reached, or the request ended before completion.
                await api._release_reservation(reservation)
                if source is None:
                    return
            elif not await api._settle_source_reservation(reservation, source=source, model=model, usage=usage):
                failure = ("usage_settlement_failed", "Image usage settlement failed")
            code, message = (error_code, error_message) if not completed else failure or (None, None)
            await api._log_source_chat_completion(
                request,
                source=source,
                api_key=api_key,
                model=model,
                status="success" if completed and failure is None else "error",
                usage=usage if completed else None,
                error_code=code,
                error_message=message,
                upstream_status_code=upstream_status,
                preserve_unknown_cost=True,
            )
        finally:
            await transport.aclose()

    def capture_usage(raw: JsonValue) -> None:
        nonlocal usage, completed
        usage = ImageUsage.model_validate(raw).source_usage() if raw is not None else None
        if usage is None and api._reservation_requires_usage(reservation):
            raise ImageFailure(502, "usage_unavailable", "OpenAI image response lacks usage for a limited API key")
        completed = True

    try:
        attempted: set[str] = set()
        last_refusal: ModelSourceForwardingError | None = None
        while True:
            try:
                source = await select_image_source(model, api_key, attempted)
            except ImageFailure:
                if last_refusal is None:
                    raise
                raise last_refusal from None
            attempted.add(source.id)
            assert source.api_key_encrypted is not None
            session = await stack.enter_async_context(lease_model_source_session())
            response = await stack.enter_async_context(
                session.post(
                    f"{source.base_url.rstrip('/')}/images/{operation}",
                    json={**body, "model": _upstream_model(source, model)},
                    headers={"Authorization": f"Bearer {TokenEncryptor().decrypt(source.api_key_encrypted)}"},
                    timeout=aiohttp.ClientTimeout(total=source.timeout_seconds or 600, sock_connect=10),
                    allow_redirects=False,
                )
            )
            upstream_status = response.status
            if response.status < 400:
                break
            error_payload = await _read_error_body(response, source=source, scheduler=REAL_SCHEDULER)
            refusal = _upstream_status_error(response, source, encryptor=None, error_payload=error_payload)
            if response.status not in (401, 429):
                raise refusal
            # An explicit refusal before any output: another account of the pool may serve the request.
            await pooled_accounts.record_failure(
                source.id, model, response.status, refusal.retry_after, api._source_error_code(refusal.payload)
            )
            last_refusal = refusal
            await stack.aclose()
        if body.get("stream") is True:
            if "text/event-stream" not in response.headers.get("Content-Type", ""):
                raise ImageFailure(502, "upstream_error", "OpenAI did not return an image event stream")

            async def events() -> AsyncIterator[bytes]:
                nonlocal error_code, error_message
                try:
                    async for chunk in passthrough_events(response.content.iter_any(), capture_usage):
                        yield chunk
                    if not completed:
                        raise ImageFailure(502, "stream_incomplete", "OpenAI image stream ended without completion")
                except (ImageFailure, ValueError, aiohttp.ClientError, TimeoutError) as exc:
                    failure = (
                        exc
                        if isinstance(exc, ImageFailure)
                        else ImageFailure(502, "upstream_error", "Invalid or interrupted OpenAI image stream")
                    )
                    error_code = failure.payload["error"]["code"]
                    error_message = failure.payload["error"]["message"]
                    event = {"type": "error", "error": {"code": error_code, "message": error_message}}
                    yield f"event: error\ndata: {json.dumps(event)}\n\n".encode()
                finally:
                    await _await_cleanup_deferring_cancellation(finish())

            handed_off = True
            streamed = OwnedImageStream(events(), finish)
            streamed.headers.update(headers)
            return streamed
        raw = await response.content.read(MAX_IMAGE_RESPONSE_BYTES + 1)
        if len(raw) > MAX_IMAGE_RESPONSE_BYTES:
            raise ImageFailure(502, "upstream_error", "OpenAI image response exceeds the allowed size")
        result = json.loads(raw)
        capture_usage(result.get("usage") if isinstance(result, dict) else None)
        await _await_cleanup_deferring_cancellation(finish())
        return Response(raw, status_code=response.status, media_type="application/json", headers=headers)
    except ModelSourceForwardingError as exc:
        error_code, error_message = api._source_error_code(exc.payload), api._source_error_message(exc.payload)
        return api._logged_error_json_response(
            request, exc.status_code, exc.payload, headers=api._source_error_response_headers(headers, exc)
        )
    except ImageFailure as exc:
        error_code, error_message = exc.payload["error"]["code"], exc.payload["error"]["message"]
        retry = {"Retry-After": exc.retry_after} if exc.retry_after else {}
        return api._logged_error_json_response(request, exc.status, exc.payload, headers={**headers, **retry})
    except (ValueError, ValidationError, aiohttp.ClientError, TimeoutError):
        error_code, error_message = "upstream_error", "Invalid or interrupted OpenAI image response"
        return api._logged_error_json_response(
            request, 502, openai_error(error_code, error_message, error_type="server_error"), headers=headers
        )
    finally:
        if not handed_off:
            await _await_cleanup_deferring_cancellation(finish())
