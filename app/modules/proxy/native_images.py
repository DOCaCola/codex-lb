from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.requests import ClientDisconnect

from app.core.clients.proxy import CodexControlResponse, ProxyResponseError
from app.core.exceptions import ProxyModelNotAllowed, ProxyRateLimitError
from app.core.utils.request_id import ensure_request_id
from app.dependencies import ProxyContext
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy.images_observability import IMAGE_ROUTE_STARTED_AT_STATE, record_images_route_observability
from app.modules.proxy.images_service import make_invalid_request_error
from app.modules.proxy.request_policy import openai_validation_error


class NativeImageUrl(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    # Codex can reuse image URLs from conversation history as well as data
    # URLs. Forward them to upstream; never fetch reference URLs locally.
    image_url: str = Field(min_length=1)


class NativeImageRequest(BaseModel):
    """Validate the routing envelope without narrowing the upstream image API."""

    model_config = ConfigDict(extra="allow", strict=True)
    model: str = Field(default="gpt-image-2", pattern=r"^gpt-image-")
    prompt: str = Field(min_length=1)
    images: list[NativeImageUrl] | None = None


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
        if isinstance(body, dict) and isinstance(body.get("usage"), dict):
            return NativeImageUsage.model_validate(body["usage"])
    except (ValueError, UnicodeDecodeError):
        pass
    # Missing or unreadable usage is not evidence of token consumption.
    return NativeImageUsage()


async def native_image_response(
    request: Request,
    context: ProxyContext,
    api_key: ApiKeyData | None,
    *,
    operation: Literal["generations", "edits"],
) -> Response:
    # Route-owned policy helpers are shared with the public Images adapter.
    from app.modules.proxy import api

    started_at: float = getattr(request.state, IMAGE_ROUTE_STARTED_AT_STATE)
    model: str | None = None
    status = 500
    outcome = "invalid_request"
    denial = await api._required_capability_http_transport_denial(request, api_key)
    if denial is not None:
        api._record_required_capability_image_transport_denial(
            request,
            route=operation,
            model=None,
            stream=False,
        )
        return denial
    try:
        raw = await request.body()
        try:
            body = json.loads(raw)
            payload = NativeImageRequest.model_validate(body)
            model = payload.model
            if operation == "edits" and not payload.images:
                status = 400
                return api._logged_error_json_response(
                    request,
                    status,
                    make_invalid_request_error("At least one images[].image_url is required.", param="images"),
                )
        except ValidationError as exc:
            status = 400
            return api._logged_error_json_response(request, status, openai_validation_error(exc))
        except (ValueError, UnicodeDecodeError):
            status = 400
            return api._logged_error_json_response(
                request,
                status,
                make_invalid_request_error("Expected a JSON request body.", param="prompt"),
            )
        model = api._effective_model_for_api_key(api_key, payload.model)
        if not model.startswith("gpt-image-"):
            status = 400
            return api._logged_error_json_response(
                request,
                status,
                make_invalid_request_error("This API key is not configured for an image model.", param="model"),
            )
        api.validate_model_access(api_key, model)
        if body.get("model") != model:
            body["model"] = model
            raw = json.dumps(body).encode()
        reservation = await api._enforce_request_limits(
            api_key,
            request_model=model,
            request_service_tier=None,
        )
        usage = NativeImageUsage()
        settled = False

        async def settle(_account_id: str, response: CodexControlResponse) -> bool:
            nonlocal usage, settled
            usage = reported_image_usage(response)
            await api._finalize_image_reservation(
                context.service,
                api_key,
                reservation,
                model=model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
            )
            settled = True
            return True

        outcome = "upstream_error"
        try:
            response = await context.service.codex_control_request(
                f"images/{operation}",
                method="POST",
                payload=raw,
                query_params=list(request.query_params.multi_items()),
                headers={**dict(request.headers), "content-type": "application/json"},
                codex_session_affinity=False,
                api_key=api_key,
                image_model=model,
                success_gate=settle,
            )
            status = response.status_code
            outcome = "success" if 200 <= status < 300 else "image_error"
            safe_headers = api._codex_control_downstream_headers(response.headers)
            for name, value in response.headers.items():
                if name.lower() in {"x-codex-imagegen-request-id", "retry-after"}:
                    safe_headers[name] = value
            return Response(response.body, status_code=status, headers=safe_headers)
        finally:
            if not settled:
                await context.service.settle_image_api_key_usage(
                    api_key,
                    reservation,
                    model=model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cached_input_tokens=usage.cached_input_tokens,
                    request_id=ensure_request_id(None),
                )
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
        return api._logged_error_json_response(request, status, exc.payload)
    finally:
        record_images_route_observability(
            route=operation,
            model=model,
            stream=False,
            status=status,
            outcome=outcome,
            started_at=started_at,
        )
