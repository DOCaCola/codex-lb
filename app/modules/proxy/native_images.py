from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncGenerator, Mapping, Sequence
from typing import Literal

import anyio
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.requests import ClientDisconnect

from app.core.clients.proxy import NativeImageStream, ProxyResponseError
from app.core.errors import OpenAIErrorEnvelope, openai_error
from app.core.exceptions import ProxyModelNotAllowed, ProxyRateLimitError
from app.core.request_locality import resolve_request_client_host
from app.dependencies import ProxyContext
from app.modules.api_keys.service import ApiKeyData, ApiKeyUsageReservationData
from app.modules.proxy.images_observability import IMAGE_ROUTE_STARTED_AT_STATE, record_images_route_observability
from app.modules.proxy.native_image_usage import NativeImageAccounting
from app.modules.proxy.request_policy import openai_validation_error

ImageOperation = Literal["generations", "edits"]
DEFAULT_IMAGE_MODEL = "gpt-image-2"
_PASSTHROUGH_RESPONSE_HEADERS = frozenset({"x-codex-imagegen-request-id", "retry-after"})
_INTEGER_FORM_FIELDS = frozenset({"n", "output_compression", "partial_images"})


class NativeImageUrl(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    # Codex can reuse image URLs from conversation history as well as data
    # URLs. Forward them to upstream; never fetch reference URLs locally.
    image_url: str = Field(min_length=1)


class NativeImageRequest(BaseModel):
    """Validate the routing envelope without narrowing the upstream image API."""

    model_config = ConfigDict(extra="allow", strict=True)
    model: str = Field(default=DEFAULT_IMAGE_MODEL, pattern=r"^gpt-image-")
    prompt: str = Field(min_length=1)
    images: list[NativeImageUrl] | None = None


def image_invalid_request_error(message: str, *, param: str | None = None) -> OpenAIErrorEnvelope:
    envelope = openai_error("invalid_request_error", message, error_type="invalid_request_error")
    if param:
        envelope["error"]["param"] = param
    return envelope


def native_edit_body(
    text_fields: Sequence[tuple[str, str]],
    images: Sequence[tuple[bytes, str | None]],
    mask: tuple[bytes, str | None] | None,
) -> dict[str, object]:
    """Express a multipart Images edit in the native JSON shape.

    Text fields pass through by name; only the numeric and boolean fields of
    the Images API are typed. Uploaded files become data URLs.
    """
    body: dict[str, object] = {key: _typed_form_value(key, value) for key, value in text_fields}
    body["images"] = [{"image_url": _data_url(data, content_type)} for data, content_type in images]
    if mask is not None:
        body["mask"] = {"image_url": _data_url(*mask)}
    return body


def _typed_form_value(key: str, value: str) -> object:
    stripped = value.strip()
    if key in _INTEGER_FORM_FIELDS and stripped.isdecimal():
        return int(stripped)
    if key == "stream" and stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    return value


def _data_url(data: bytes, content_type: str | None) -> str:
    mime_type = (content_type or "image/png").strip() or "image/png"
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


async def native_image_response(
    request: Request,
    context: ProxyContext,
    api_key: ApiKeyData | None,
    *,
    operation: ImageOperation,
) -> Response:
    """Forward a Codex native image request."""
    from app.modules.proxy import api

    started_at: float = getattr(request.state, IMAGE_ROUTE_STARTED_AT_STATE)
    denial = await api._required_capability_http_transport_denial(request, api_key)
    if denial is not None:
        api._record_required_capability_image_transport_denial(request, route=operation, model=None, stream=False)
        return denial
    try:
        body: object = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        return _rejected(
            request,
            image_invalid_request_error("Expected a JSON request body.", param="prompt"),
            operation=operation,
            model=None,
            stream=False,
            started_at=started_at,
            rate_limit_headers={},
        )
    return await forward_native_image(
        request,
        context,
        api_key,
        operation=operation,
        body=body,
        started_at=started_at,
        rate_limit_headers={},
    )


async def public_image_response(
    request: Request,
    context: ProxyContext,
    api_key: ApiKeyData | None,
    *,
    operation: ImageOperation,
    body: object,
    started_at: float,
) -> Response:
    """Forward an OpenAI-compatible ``/v1/images/*`` request natively."""
    from app.modules.proxy import api

    rate_limit_headers = await api._rate_limit_headers_for_request(context, api_key)
    return await forward_native_image(
        request,
        context,
        api_key,
        operation=operation,
        body=body,
        started_at=started_at,
        rate_limit_headers=rate_limit_headers,
    )


async def forward_native_image(
    request: Request,
    context: ProxyContext,
    api_key: ApiKeyData | None,
    *,
    operation: ImageOperation,
    body: object,
    started_at: float,
    rate_limit_headers: Mapping[str, str],
) -> Response:
    """Send an Images request to the native ChatGPT image endpoint.

    The request is forwarded unchanged apart from the enforced or default
    public image model; the native status, body and event stream reach the
    client unchanged.
    """
    from app.modules.proxy import api

    model: str | None = None
    stream = isinstance(body, dict) and body.get("stream") is True
    status = 500
    outcome = "invalid_request"
    stream_owns_observability = False
    try:
        if not isinstance(body, dict):
            status = 400
            return api._logged_error_json_response(
                request,
                status,
                image_invalid_request_error("Expected a JSON object request body."),
                headers=dict(rate_limit_headers),
            )
        if isinstance(requested_model := body.get("model"), str):
            model = requested_model
        try:
            payload = NativeImageRequest.model_validate(body)
        except ValidationError as exc:
            status = 400
            return api._logged_error_json_response(
                request, status, openai_validation_error(exc), headers=dict(rate_limit_headers)
            )
        if operation == "edits" and not payload.images:
            status = 400
            return api._logged_error_json_response(
                request,
                status,
                image_invalid_request_error("At least one images[].image_url is required.", param="images"),
                headers=dict(rate_limit_headers),
            )
        model = api._effective_model_for_api_key(api_key, payload.model)
        if not model.startswith("gpt-image-"):
            status = 400
            return api._logged_error_json_response(
                request,
                status,
                image_invalid_request_error("This API key is not configured for an image model.", param="model"),
                headers=dict(rate_limit_headers),
            )
        api.validate_model_access(api_key, model)
        body["model"] = model
        reservation = await api._enforce_request_limits(api_key, request_model=model, request_service_tier=None)
        accounting = NativeImageAccounting(model=model)
        outcome = "upstream_error"
        try:
            result = await context.service.native_image_request(
                operation,
                payload=json.dumps(body).encode(),
                headers={**dict(request.headers), "content-type": "application/json"},
                api_key=api_key,
                accounting=accounting,
                client_ip=resolve_request_client_host(request),
            )
        except BaseException:
            await _settle_image_usage(context, api_key, reservation, accounting)
            raise
        status = result.status_code
        headers = {**_downstream_headers(result.headers), **rate_limit_headers}
        if isinstance(result, NativeImageStream):
            stream_owns_observability = True
            return StreamingResponse(
                _settled_stream(
                    result,
                    context=context,
                    api_key=api_key,
                    reservation=reservation,
                    accounting=accounting,
                    operation=operation,
                    started_at=started_at,
                ),
                status_code=status,
                headers=headers,
                media_type="text/event-stream",
            )
        await _settle_image_usage(context, api_key, reservation, accounting)
        outcome = "success" if 200 <= status < 300 else "image_error"
        return Response(result.body, status_code=status, headers=headers)
    except (asyncio.CancelledError, ClientDisconnect):
        status = 499
        outcome = "client_disconnected"
        raise
    except ProxyModelNotAllowed:
        status = 403
        outcome = "model_not_allowed"
        raise
    except ProxyRateLimitError:
        status = 429
        outcome = "rate_limited"
        raise
    except ProxyResponseError as exc:
        status = exc.status_code
        return api._logged_error_json_response(request, status, exc.payload, headers=dict(rate_limit_headers))
    finally:
        if not stream_owns_observability:
            record_images_route_observability(
                route=operation,
                model=model,
                stream=stream,
                status=status,
                outcome=outcome,
                started_at=started_at,
            )


def _rejected(
    request: Request,
    error: OpenAIErrorEnvelope,
    *,
    operation: ImageOperation,
    model: str | None,
    stream: bool,
    started_at: float,
    rate_limit_headers: Mapping[str, str],
) -> Response:
    from app.modules.proxy import api

    record_images_route_observability(
        route=operation,
        model=model,
        stream=stream,
        status=400,
        outcome="invalid_request",
        started_at=started_at,
    )
    return api._logged_error_json_response(request, 400, error, headers=dict(rate_limit_headers))


def _downstream_headers(headers: Mapping[str, str]) -> dict[str, str]:
    from app.modules.proxy import api

    safe_headers = api._codex_control_downstream_headers(headers)
    for name, value in headers.items():
        if name.lower() in _PASSTHROUGH_RESPONSE_HEADERS:
            safe_headers[name] = value
    return safe_headers


async def _settle_image_usage(
    context: ProxyContext,
    api_key: ApiKeyData | None,
    reservation: ApiKeyUsageReservationData | None,
    accounting: NativeImageAccounting,
) -> None:
    from app.modules.proxy import api

    usage = accounting.usage
    await api._finalize_image_reservation(
        context.service,
        api_key,
        reservation,
        model=accounting.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=usage.cached_input_tokens,
    )


async def _settled_stream(
    stream: NativeImageStream,
    *,
    context: ProxyContext,
    api_key: ApiKeyData | None,
    reservation: ApiKeyUsageReservationData | None,
    accounting: NativeImageAccounting,
    operation: ImageOperation,
    started_at: float,
) -> AsyncGenerator[bytes, None]:
    outcome = "client_disconnected"
    try:
        async for chunk in stream.chunks:
            yield chunk
        outcome = accounting.stream_outcome or "stream_closed"
    except ProxyResponseError:
        outcome = "upstream_error"
        raise
    finally:
        with anyio.CancelScope(shield=True):
            try:
                await stream.chunks.aclose()
                await _settle_image_usage(context, api_key, reservation, accounting)
            finally:
                record_images_route_observability(
                    route=operation,
                    model=accounting.model,
                    stream=True,
                    status=stream.status_code,
                    outcome=outcome,
                    started_at=started_at,
                )
