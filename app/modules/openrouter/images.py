"""Public Images adapter. Native Codex image routes never enter this module."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import AsyncExitStack
from typing import Literal

import aiohttp
from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.responses import JSONResponse, StreamingResponse
from starlette.types import Receive, Scope, Send

from app.core.clients.http import lease_model_source_session
from app.core.clock import REAL_SCHEDULER
from app.core.crypto import TokenEncryptor
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_mapping
from app.core.utils.shared_future import _await_cleanup_deferring_cancellation
from app.db.models import ModelSource
from app.db.session import detach_session_objects, get_background_session
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_sources.forwarding import SourceStreamTransport, SourceUsage
from app.modules.model_sources.repository import ModelSourcesRepository
from app.modules.model_sources.selection import allowed_source_ids_for_api_key
from app.modules.openrouter import routing
from app.modules.openrouter.protocol import normalize_error
from app.modules.openrouter.schemas import ImageEndpoint, ImageModel

MAX_IMAGE_RESPONSE_BYTES = 100 * 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024


class ImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    prompt: str = Field(min_length=1)
    n: int = Field(default=1, ge=1, le=10)
    stream: bool = False
    size: str | None = None
    resolution: str | None = None
    aspect_ratio: str | None = None
    quality: str | None = None
    background: str | None = None
    output_format: Literal["png", "jpeg", "webp"] | None = None
    output_compression: int | None = Field(default=None, ge=0, le=100)
    seed: int | None = None
    moderation: str | None = None
    user: str | None = None
    response_format: Literal["b64_json"] = "b64_json"


class ImageUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    def source_usage(self) -> SourceUsage:
        return SourceUsage(self.prompt_tokens, self.completion_tokens, reported_cost_usd=self.cost)


class ImageData(BaseModel):
    model_config = ConfigDict(extra="allow")
    b64_json: str = Field(min_length=1)


class ImageResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    created: int = Field(ge=0)
    data: list[ImageData] = Field(min_length=1)
    usage: ImageUsage | None = None


class ImageError(Exception):
    def __init__(self, status: int, message: str, *, code: str = "upstream_error", retry_after: str | None = None):
        self.status = status
        self.payload = {
            "error": {
                "message": message,
                "code": code,
                "type": "invalid_request_error" if status < 500 else "server_error",
            }
        }
        self.retry_after = retry_after


async def select_image_source(model: str, api_key: ApiKeyData | None) -> tuple[ModelSource, ImageModel]:
    allowed = allowed_source_ids_for_api_key(api_key)
    async with get_background_session() as session:
        sources = await ModelSourcesRepository(session).list_enabled_sources()
        candidates = []
        descriptions = {}
        for source in sources:
            if source.kind != "openrouter" or (allowed is not None and source.id not in allowed):
                continue
            for row in source.models:
                if row.model == model and row.is_enabled:
                    image = json.loads(row.raw_metadata_json or "{}").get("image")
                    if image is not None:
                        candidates.append(source)
                        descriptions[source.id] = ImageModel.model_validate(image)
        source = await routing.select_available(session, candidates, model)
        detach_session_objects(session)
    if source is None:
        raise ImageError(
            404, "No enabled, permitted OpenRouter image model matches this request", code="model_not_found"
        )
    remaining = await routing.cooldown_remaining(source.id, model)
    if remaining:
        raise ImageError(
            429, "OpenRouter image account is cooling down", code="rate_limit_exceeded", retry_after=str(remaining)
        )
    return source, descriptions[source.id]


def project_image_request(
    payload: ImageRequest,
    image: ImageModel,
    references: list[tuple[bytes, str | None]],
) -> dict[str, JsonValue]:
    params = payload.model_dump(exclude_none=True, exclude_unset=True, exclude={"model", "response_format"})
    params["model"] = image.id
    if references:
        refs: list[JsonValue] = []
        for data, mime in references:
            if mime not in {"image/png", "image/jpeg", "image/webp"}:
                raise ImageError(400, "Reference uploads must be PNG, JPEG or WebP", code="unsupported_parameter")
            refs.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}
            )
        params["input_references"] = refs
    if payload.stream and payload.n != 1:
        raise ImageError(400, "Streaming images requires n=1", code="unsupported_parameter")

    def supports(endpoint: ImageEndpoint) -> bool:
        if payload.stream and not endpoint.supports_streaming:
            return False
        for name, value in params.items():
            if name in {"model", "prompt", "stream", "user", "size", "output_format"}:
                continue
            if name == "moderation":
                if name not in endpoint.allowed_passthrough_parameters:
                    return False
                continue
            capability = endpoint.supported_parameters.get(name)
            if capability is None:
                return False
            measured = len(value) if name == "input_references" else value
            if capability.type == "enum" and measured not in capability.values:
                return False
            if capability.type == "range" and (
                not isinstance(measured, int)
                or (capability.min is not None and measured < capability.min)
                or (capability.max is not None and measured > capability.max)
            ):
                return False
        return True

    endpoints = [endpoint for endpoint in image.endpoint_details if supports(endpoint)]
    if not endpoints:
        raise ImageError(400, "No image endpoint supports the requested parameters", code="unsupported_parameter")
    # Restrict provider routing to endpoints validated above; never change the model.
    provider: dict[str, JsonValue] = {
        "sort": "price",
        "only": [endpoint.provider_tag or endpoint.provider_slug for endpoint in endpoints],
    }
    moderation = params.pop("moderation", None)
    if moderation is not None:
        provider["options"] = {endpoint.provider_slug: {"moderation": moderation} for endpoint in endpoints}
    params["provider"] = provider
    return params


async def bounded_body(response: aiohttp.ClientResponse, maximum: int) -> bytes:
    body = bytearray()
    async for chunk in response.content.iter_chunked(65536):
        body.extend(chunk)
        if len(body) > maximum:
            raise ImageError(502, "OpenRouter image response exceeds the allowed size")
    return bytes(body)


async def image_events(response: aiohttp.ClientResponse) -> AsyncIterator[dict[str, JsonValue]]:
    buffer = bytearray()
    data_lines: list[bytes] = []
    total = 0
    async for chunk in response.content.iter_chunked(65536):
        total += len(chunk)
        if total > MAX_IMAGE_RESPONSE_BYTES:
            raise ImageError(502, "OpenRouter image stream exceeds the allowed size")
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, rest = buffer.partition(b"\n")
            buffer = bytearray(rest)
            line = line.rstrip(b"\r")
            if line.startswith(b"data:"):
                data_lines.append(bytes(line[5:]).lstrip(b" "))
                continue
            if line or not data_lines:
                continue
            data = b"\n".join(data_lines)
            data_lines.clear()
            if data == b"[DONE]":
                return
            event = json.loads(data)
            if not isinstance(event, dict):
                raise ImageError(502, "Invalid OpenRouter image event")
            yield event


class OwnedImageStream(StreamingResponse):
    def __init__(self, body: AsyncIterator[bytes], cleanup: Callable[[], Awaitable[None]]):
        super().__init__(body, media_type="text/event-stream")
        self.cleanup = cleanup

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            await _await_cleanup_deferring_cancellation(self.cleanup())


async def image_response(
    request: Request,
    body: Mapping[str, JsonValue],
    api_key: ApiKeyData | None,
    *,
    operation: Literal["generations", "edits"],
    images: list[tuple[bytes, str | None]] | None = None,
    has_mask: bool = False,
) -> Response:
    from app.modules.proxy import api

    try:
        payload = ImageRequest.model_validate(body)
        api.validate_model_access(api_key, payload.model)
        if has_mask:
            raise ImageError(400, "OpenRouter image masks are not supported", code="unsupported_parameter")
        source, image = await select_image_source(payload.model, api_key)
        outbound = project_image_request(payload, image, images or [])
    except ValidationError as exc:
        return api._logged_error_json_response(request, 400, api.openai_validation_error(exc))
    except ImageError as exc:
        return api._logged_error_json_response(
            request, exc.status, exc.payload, headers={"Retry-After": exc.retry_after} if exc.retry_after else None
        )

    reservation = await api._enforce_request_limits(api_key, request_model=payload.model, request_service_tier=None)
    stack = AsyncExitStack()
    transport = SourceStreamTransport(stack, scheduler=REAL_SCHEDULER)
    usage: SourceUsage | None = None
    completed = False
    finalized = False
    handed_off = False
    upstream_status: int | None = None
    error_code = "client_disconnected"
    error_message = "Image request ended before completion"

    async def finish() -> None:
        nonlocal finalized
        if finalized:
            return
        finalized = True
        try:
            settlement_failed = False
            if completed:
                settlement_failed = not await api._settle_source_reservation(
                    reservation, source=source, model=payload.model, usage=usage
                )
            else:
                await api._release_reservation(reservation)
            await api._log_source_chat_completion(
                request,
                source=source,
                api_key=api_key,
                model=payload.model,
                status="success" if completed and not settlement_failed else "error",
                usage=usage if completed else None,
                error_code="usage_settlement_failed" if settlement_failed else None if completed else error_code,
                error_message="Image usage settlement failed"
                if settlement_failed
                else None
                if completed
                else error_message,
                upstream_status_code=upstream_status,
                preserve_unknown_cost=True,
            )
            if settlement_failed:
                raise ImageError(502, "Image usage settlement failed", code="usage_settlement_failed")
        finally:
            await transport.aclose()

    def capture_usage(raw: JsonValue) -> None:
        nonlocal usage
        usage = ImageUsage.model_validate(raw).source_usage() if raw is not None else None
        if api._reservation_requires_usage(reservation) and (usage is None or usage.reported_cost_usd is None):
            raise ImageError(
                502, "OpenRouter image response lacks usage or cost for a limited key", code="usage_unavailable"
            )

    try:
        assert source.api_key_encrypted is not None
        token = TokenEncryptor().decrypt(source.api_key_encrypted)
        session = await stack.enter_async_context(lease_model_source_session())
        response = await stack.enter_async_context(
            session.post(
                source.base_url.rstrip("/") + "/images",
                json=outbound,
                headers={"Authorization": f"Bearer {token}", "X-Title": "codex-lb"},
                timeout=aiohttp.ClientTimeout(total=source.timeout_seconds or 600, sock_connect=10),
                allow_redirects=False,
            )
        )
        upstream_status = response.status
        if not 200 <= response.status < 300:
            raw_error = await bounded_body(response, MAX_ERROR_BYTES)
            try:
                data = json.loads(raw_error)
            except ValueError:
                data = {}
            normalized = normalize_error(dict(data), response.status) if is_json_mapping(data) else {}
            error = normalized.get("error")
            if not is_json_mapping(error):
                error = {"code": str(response.status), "message": "OpenRouter image request failed"}
            message = str(error.get("message", "OpenRouter image request failed")).replace(token, "[redacted]")
            if response.status in {401, 402, 429} or response.status >= 500:
                await routing.record_failure(
                    source.id, payload.model, response.status, response.headers.get("Retry-After")
                )
            raise ImageError(
                response.status if response.status >= 400 else 502,
                message,
                code=str(error.get("code", "upstream_error")),
                retry_after=response.headers.get("Retry-After"),
            )
        if payload.stream:
            if "text/event-stream" not in response.headers.get("Content-Type", ""):
                raise ImageError(502, "OpenRouter did not return an image event stream")

            async def stream() -> AsyncIterator[bytes]:
                nonlocal completed, error_code, error_message
                try:
                    async for event in image_events(response):
                        kind = event.get("type")
                        if kind == "error":
                            error = event.get("error")
                            if is_json_mapping(error):
                                raise ImageError(
                                    502,
                                    str(error.get("message", "OpenRouter image generation failed")).replace(
                                        token, "[redacted]"
                                    ),
                                    code=str(error.get("code", "upstream_error")),
                                )
                            raise ImageError(502, "OpenRouter image generation failed")
                        if kind not in {"image_generation.partial_image", "image_generation.completed"}:
                            continue
                        ImageData.model_validate(event)
                        if kind == "image_generation.completed":
                            capture_usage(event.get("usage"))
                            completed = True
                            await _await_cleanup_deferring_cancellation(finish())
                        if operation == "edits":
                            event["type"] = str(kind).replace("image_generation.", "image_edit.")
                        if usage is not None and kind == "image_generation.completed":
                            event["usage"] = public_usage(usage)
                        yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()
                        if completed:
                            return
                    raise ImageError(502, "OpenRouter image stream ended without completion", code="stream_incomplete")
                except (ImageError, ValueError, aiohttp.ClientError, TimeoutError) as exc:
                    error_code = exc.payload["error"]["code"] if isinstance(exc, ImageError) else "upstream_error"
                    error_message = (
                        exc.payload["error"]["message"]
                        if isinstance(exc, ImageError)
                        else "Invalid or interrupted OpenRouter image stream"
                    )
                    event = {"type": "error", "error": {"code": error_code, "message": error_message}}
                    yield f"event: error\ndata: {json.dumps(event)}\n\n".encode()
                finally:
                    await _await_cleanup_deferring_cancellation(finish())

            handed_off = True
            return OwnedImageStream(stream(), finish)
        result = ImageResult.model_validate_json(await bounded_body(response, MAX_IMAGE_RESPONSE_BYTES))
        capture_usage(result.usage.model_dump() if result.usage is not None else None)
        completed = True
        await _await_cleanup_deferring_cancellation(finish())
        public = result.model_dump(mode="json", exclude_none=True)
        if usage is not None:
            public["usage"] = public_usage(usage)
        return JSONResponse(public)
    except ImageError as exc:
        error_code, error_message = exc.payload["error"]["code"], exc.payload["error"]["message"]
        return api._logged_error_json_response(
            request, exc.status, exc.payload, headers={"Retry-After": exc.retry_after} if exc.retry_after else None
        )
    except (ValueError, aiohttp.ClientError, TimeoutError):
        error_code, error_message = "upstream_error", "Invalid or interrupted OpenRouter image response"
        return api._logged_error_json_response(
            request, 502, {"error": {"code": error_code, "message": error_message, "type": "server_error"}}
        )
    finally:
        if not handed_off:
            await _await_cleanup_deferring_cancellation(finish())


def public_usage(usage: SourceUsage) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
    }
    if usage.reported_cost_usd is not None:
        result["cost"] = usage.reported_cost_usd
    return result
