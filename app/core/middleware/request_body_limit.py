from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, cast

from fastapi import FastAPI
from starlette._utils import get_route_path
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import dashboard_error, openai_error
from app.core.ingress_limits import MAX_CONFIGURABLE_RESPONSES_BODY_BYTES, MAX_DECOMPRESSED_BODY_BYTES
from app.core.ingress_policy import responses_body_limit_bytes
from app.core.middleware.multipart_content_encoding import (
    is_route_owned_multipart_operation,
    multipart_content_encoding_gate_was_applied,
)
from app.core.runtime_logging import log_error_response

REQUEST_BODY_TOO_LARGE_MESSAGE = "Request body exceeds the maximum allowed size"

_RESPONSES_INGRESS_PATHS = frozenset(
    {
        "/backend-api/codex/responses",
        "/v1/responses",
        "/backend-api/codex/responses/compact",
        "/v1/responses/compact",
        "/internal/bridge/responses",
    }
)
_OPENAI_INGRESS_PATH_PREFIXES = (
    "/api/codex",
    "/backend-api",
    "/internal/bridge",
    "/v1",
)
_REQUEST_BODY_TOO_LARGE_STATE = "_codex_lb_request_body_too_large"

logger = logging.getLogger(__name__)


class _RequestBodyTooLarge(Exception):
    pass


@dataclass(frozen=True)
class _BodyLimitExceeded:
    """Retain diagnostic counts, never an exception traceback or body bytes."""

    limit: int
    measured_bytes: int


def request_body_limit_for_path(path: str) -> int:
    if path.rstrip("/") in _RESPONSES_INGRESS_PATHS:
        return responses_body_limit_bytes()
    return MAX_DECOMPRESSED_BODY_BYTES


def request_body_too_large_response(
    request: Request,
    *,
    limit: int,
    measured_bytes: int,
    measurement: Literal["declared_wire", "observed_wire_lower_bound", "decoded_lower_bound"],
) -> JSONResponse:
    """Describe local Responses admission without implying a provider verdict."""
    code = "payload_too_large"
    message = REQUEST_BODY_TOO_LARGE_MESSAGE
    if get_route_path(request.scope).rstrip("/") in _RESPONSES_INGRESS_PATHS:
        code = "inbound_body_too_large"
        qualifier = "declared " if measurement == "declared_wire" else "at least "
        message = (
            f"codex-lb refused the request before upstream dispatch: {qualifier}{measured_bytes} bytes "
            f"exceeds the configured {limit}-byte budget (measurement={measurement}). "
            "This is a local proxy limit, not a provider refusal. Increase "
            f"CODEX_LB_RESPONSES_BODY_LIMIT_BYTES (maximum {MAX_CONFIGURABLE_RESPONSES_BODY_BYTES}) "
            "and restart, or reduce the input."
        )
    return request_ingress_error_response(request, status_code=413, code=code, message=message)


def _path_belongs_to(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _uses_openai_ingress_errors(path: str) -> bool:
    return any(_path_belongs_to(path, prefix) for prefix in _OPENAI_INGRESS_PATH_PREFIXES)


def request_ingress_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    uses_openai_errors = _uses_openai_ingress_errors(get_route_path(request.scope))
    response_code = "invalid_request_error" if uses_openai_errors and code == "invalid_request" else code
    log_error_response(
        logger,
        request,
        status_code,
        response_code,
        message,
        category="openai_error_response" if uses_openai_errors else "dashboard_error_response",
    )
    if uses_openai_errors:
        return JSONResponse(
            status_code=status_code,
            content=openai_error(response_code, message, error_type="invalid_request_error"),
        )
    return JSONResponse(
        status_code=status_code,
        content=dashboard_error(response_code, message),
    )


def request_body_limit_error_response(request: Request) -> JSONResponse | None:
    error = cast(_BodyLimitExceeded | None, getattr(request.state, _REQUEST_BODY_TOO_LARGE_STATE, None))
    if error is None:
        return None
    return request_body_too_large_response(
        request, limit=error.limit, measured_bytes=error.measured_bytes, measurement="observed_wire_lower_bound"
    )


def _mark_request_body_limit_exceeded(scope: Scope, error: _BodyLimitExceeded) -> None:
    state = scope.setdefault("state", {})
    state[_REQUEST_BODY_TOO_LARGE_STATE] = error


def _is_unencoded_multipart(headers: Headers) -> bool:
    content_type = headers.get("content-type", "")
    media_type = content_type.partition(";")[0].strip().lower()
    return media_type == "multipart/form-data" and headers.get("content-encoding") is None


def _declared_content_length(headers: Headers) -> int | None:
    value = headers.get("content-length")
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        route_owned_multipart = is_route_owned_multipart_operation(scope) and _is_unencoded_multipart(headers)
        if multipart_content_encoding_gate_was_applied(scope) or route_owned_multipart:
            await self.app(scope, receive, send)
            return

        path = get_route_path(scope)
        limit = request_body_limit_for_path(path)
        declared_length = _declared_content_length(headers)
        if declared_length is not None and declared_length > limit:
            response = request_body_too_large_response(
                Request(scope),
                limit=limit,
                measured_bytes=declared_length,
                measurement="declared_wire",
            )
            await response(scope, receive, send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    _mark_request_body_limit_exceeded(scope, _BodyLimitExceeded(limit, received))
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            response = request_body_limit_error_response(Request(scope))
            assert response is not None
            await response(scope, receive, send)


def add_request_body_limit_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestBodyLimitMiddleware)
