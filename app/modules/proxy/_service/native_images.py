from __future__ import annotations

import json
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, NoReturn, Protocol, TypeVar, cast

import anyio

from app.core.balancer import ResetPreferenceWindow, RoutingStrategy
from app.core.clients.proxy import (
    CodexControlResponse,
    NativeImageStream,
    ProxyResponseError,
    UpstreamProxyRouteTrace,
    filter_inbound_headers,
)
from app.core.clients.proxy import native_image_request as core_native_image_request
from app.core.clock import clock_for
from app.core.config.settings import get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.errors import openai_error
from app.core.resilience.toggles import bind_resilience_toggles
from app.core.upstream_proxy import ResolvedUpstreamRoute, UpstreamProxyRouteError
from app.core.utils.request_id import ensure_request_id, get_request_id
from app.db.models import Account
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy._service.support import _request_log_client_fields, _RequestLogFailureMetadata
from app.modules.proxy.affinity import _sticky_key_for_codex_control_request
from app.modules.proxy.helpers import _header_account_id, _normalize_error_code, _parse_openai_error
from app.modules.proxy.load_balancer import (
    AccountConcurrencyCaps,
    AccountLease,
    AccountSelection,
    RoutingTunables,
    effective_account_concurrency_caps,
    effective_routing_tunables,
)
from app.modules.proxy.native_image_usage import NativeImageAccounting, NativeImageStreamObserver
from app.modules.proxy.selection_errors import selection_failure_response

NativeImageOperation = Literal["generations", "edits"]
T = TypeVar("T")
_REQUEST_TRANSPORT_HTTP = "http"


class _NativeImageServiceProtocol(Protocol):
    _encryptor: Any
    _load_balancer: Any

    def _remaining_budget_seconds(self, deadline: float) -> float: ...
    async def _select_account_with_budget_compatible(self, deadline: float, **kwargs: object) -> AccountSelection: ...
    async def _ensure_fresh_with_budget_or_auth_error(self, account: Account, *, timeout_seconds: float) -> Account: ...
    async def _acquire_account_response_create_lease_or_overload(
        self,
        *,
        account_id: str,
        request_id: str,
        surface: str,
        concurrency_caps: AccountConcurrencyCaps,
        routing_tunables: RoutingTunables | None = None,
    ) -> AccountLease: ...
    async def _resolve_upstream_route_for_account(
        self, account: Account, *, operation: str
    ) -> ResolvedUpstreamRoute | None: ...
    async def _write_request_log(self, **kwargs: Any) -> None: ...


def _service_core_native_image_request() -> Callable[..., Awaitable[CodexControlResponse | NativeImageStream]]:
    service_module = sys.modules.get("app.modules.proxy.service")
    return cast(
        Callable[..., Awaitable[CodexControlResponse | NativeImageStream]],
        getattr(service_module, "core_native_image_request", core_native_image_request),
    )


def _service_global_or(name: str, fallback: T) -> T:
    service_module = sys.modules.get("app.modules.proxy.service")
    if service_module is None:
        return fallback
    return cast(T, getattr(service_module, name, fallback))


def _service_global(name: str) -> Any:
    service_module = sys.modules.get("app.modules.proxy.service")
    if service_module is None:
        raise RuntimeError("app.modules.proxy.service is not loaded")
    return getattr(service_module, name)


def _service_get_settings() -> Any:
    return _service_global_or("get_settings", get_settings)()


def _service_get_settings_cache() -> Any:
    return _service_global_or("get_settings_cache", get_settings_cache)()


def _raise_proxy_budget_exhausted() -> NoReturn:
    cast(Callable[[], NoReturn], _service_global("_raise_proxy_budget_exhausted"))()


def _request_log_failure_metadata(exc: ProxyResponseError) -> _RequestLogFailureMetadata:
    return cast(
        Callable[[ProxyResponseError], _RequestLogFailureMetadata], _service_global("_request_log_failure_metadata")
    )(exc)


def _prefer_earlier_reset_window(settings: Any) -> ResetPreferenceWindow:
    return cast(Callable[[Any], ResetPreferenceWindow], _service_global("_prefer_earlier_reset_window"))(settings)


def _routing_strategy(settings: Any) -> RoutingStrategy:
    return cast(Callable[[Any], RoutingStrategy], _service_global("_routing_strategy"))(settings)


@dataclass
class _NativeImageAttempt:
    """Request-log state for one native image dispatch."""

    request_id: str
    started_at: float
    accounting: NativeImageAccounting
    account: Account | None = None
    lease: AccountLease | None = None
    status: str = "error"
    error_code: str | None = None
    error_message: str | None = None
    upstream_status: int | None = None
    failure: _RequestLogFailureMetadata = field(default_factory=_RequestLogFailureMetadata)
    route_trace: UpstreamProxyRouteTrace = field(default_factory=UpstreamProxyRouteTrace)
    route_fail_closed_reason: str | None = None

    def record_response(self, status_code: int, body: bytes) -> None:
        self.upstream_status = status_code
        if 200 <= status_code < 300:
            self.status = "success"
            return
        # Keep raw upstream bytes for the caller; only retain a bounded error
        # code in operational logging.
        self.error_code = "upstream_image_error"
        try:
            error_body = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return
        if isinstance(error_body, dict):
            self.record_error_object(error_body.get("error"))

    def record_error_object(self, error: object) -> None:
        self.status = "error"
        self.error_code = "upstream_image_error"
        if isinstance(error, dict):
            if isinstance(code := error.get("code"), str):
                self.error_code = code[:128]
            if isinstance(message := error.get("message"), str):
                self.error_message = message

    def record_failure(self, exc: ProxyResponseError) -> None:
        self.status = "error"
        self.failure = _request_log_failure_metadata(exc)
        error = _parse_openai_error(exc.payload)
        self.error_code = self.error_code or _normalize_error_code(
            error.code if error else None,
            error.type if error else None,
        )
        self.error_message = self.error_message or (error.message if error else None)


def _sse_error_event(payload: Mapping[str, object]) -> bytes:
    error = payload.get("error")
    event = {"type": "error", "error": error if isinstance(error, dict) else payload}
    return f"event: error\ndata: {json.dumps(event, separators=(',', ':'))}\n\n".encode()


async def _prepend_chunk(first_chunk: bytes | None, rest: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
    try:
        if first_chunk is None:
            return
        yield first_chunk
        async for chunk in rest:
            yield chunk
    finally:
        await rest.aclose()


class _NativeImageMixin:
    async def native_image_request(
        self,
        operation: NativeImageOperation,
        *,
        payload: bytes,
        headers: Mapping[str, str],
        api_key: ApiKeyData | None,
        accounting: NativeImageAccounting,
        client_ip: str | None = None,
    ) -> CodexControlResponse | NativeImageStream:
        """Dispatch one native image operation on an admitted ChatGPT account.

        The POST is never replayed after dispatch. Buffered responses are
        complete when returned; a returned stream owns the account lease and
        writes the request log once it is exhausted or closed.
        """
        proxy = cast(_NativeImageServiceProtocol, self)
        clock = clock_for(self)
        base_settings = _service_get_settings()
        settings = await _service_get_settings_cache().get()
        bind_resilience_toggles(settings, startup_settings=base_settings)
        attempt = _NativeImageAttempt(
            request_id=get_request_id() or ensure_request_id(None),
            started_at=clock.monotonic(),
            accounting=accounting,
        )
        deadline = attempt.started_at + base_settings.proxy_request_budget_seconds
        request_kind = f"codex_control_images_{operation}"
        client_fields = _request_log_client_fields(headers)
        stream_handed_off = False
        try:
            selection = await proxy._select_account_with_budget_compatible(
                deadline,
                request_id=attempt.request_id,
                kind=request_kind,
                api_key=api_key,
                affinity_policy=_sticky_key_for_codex_control_request(headers, codex_session_affinity=False),
                prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
                prefer_earlier_reset_window=_prefer_earlier_reset_window(settings),
                routing_strategy=_routing_strategy(settings),
                # Image entitlement is decided by the native endpoint, not the
                # Responses catalog or a conversation's model source.
                model=None,
                redact_sensitive_details=False,
            )
            if selection.account is None:
                status_code, error_payload = selection_failure_response(selection)
                raise ProxyResponseError(status_code, error_payload)
            # Refresh before dispatch is safe. Once dispatched, the native
            # result or failure is returned without replaying billed work.
            attempt.account = await proxy._ensure_fresh_with_budget_or_auth_error(
                selection.account,
                timeout_seconds=proxy._remaining_budget_seconds(deadline),
            )
            attempt.lease = await proxy._acquire_account_response_create_lease_or_overload(
                account_id=attempt.account.id,
                request_id=attempt.request_id,
                surface="images",
                concurrency_caps=effective_account_concurrency_caps(settings),
                routing_tunables=effective_routing_tunables(settings),
            )
            route = await proxy._resolve_upstream_route_for_account(attempt.account, operation=request_kind)
            remaining_budget = proxy._remaining_budget_seconds(deadline)
            if remaining_budget <= 0:
                _raise_proxy_budget_exhausted()
            upstream = await _service_core_native_image_request()(
                operation,
                payload=payload,
                headers=filter_inbound_headers(headers),
                access_token=proxy._encryptor.decrypt(attempt.account.access_token_encrypted),
                account_id=_header_account_id(attempt.account.chatgpt_account_id),
                timeout_seconds=remaining_budget,
                route=route,
                allow_direct_egress=route is None,
                route_trace=attempt.route_trace,
            )
            if isinstance(upstream, NativeImageStream):
                attempt.upstream_status = upstream.status_code
                stream_handed_off = True
                observed = self._observed_native_image_stream(upstream, attempt, api_key, client_fields, client_ip)
                # Start the observer now: a started generator always reaches
                # its cleanup, so the lease and request log are released even
                # if the client disconnects before the body is sent.
                first_chunk = await anext(observed, None)
                return NativeImageStream(
                    status_code=upstream.status_code,
                    headers=upstream.headers,
                    chunks=_prepend_chunk(first_chunk, observed),
                )
            accounting.capture(upstream)
            attempt.record_response(upstream.status_code, upstream.body)
            if attempt.status == "success":
                await proxy._load_balancer.record_success(attempt.account)
            return upstream
        except ProxyResponseError as exc:
            attempt.record_failure(exc)
            raise
        except UpstreamProxyRouteError as exc:
            attempt.route_fail_closed_reason = exc.reason
            attempt.error_code = "upstream_proxy_unavailable"
            attempt.error_message = exc.reason
            raise ProxyResponseError(
                502,
                openai_error("upstream_proxy_unavailable", f"Upstream proxy route unavailable: {exc.reason}"),
            ) from exc
        finally:
            if not stream_handed_off:
                await self._finish_native_image_attempt(attempt, api_key, client_fields, client_ip)

    async def _observed_native_image_stream(
        self,
        upstream: NativeImageStream,
        attempt: _NativeImageAttempt,
        api_key: ApiKeyData | None,
        client_fields: tuple[str | None, str | None, str | None],
        client_ip: str | None,
    ) -> AsyncGenerator[bytes, None]:
        proxy = cast(_NativeImageServiceProtocol, self)
        observer = NativeImageStreamObserver(attempt.accounting)
        try:
            try:
                async for chunk in upstream.chunks:
                    observer.feed(chunk)
                    yield chunk
            except ProxyResponseError as exc:
                attempt.record_failure(exc)
                # Between events the client can still receive a well-formed
                # Images error event; inside an event it already holds a
                # truncated frame, so the connection is aborted instead.
                if not observer.at_event_boundary:
                    raise
                attempt.accounting.stream_outcome = "upstream_error"
                yield _sse_error_event(exc.payload)
                return
            if observer.error is not None:
                attempt.record_error_object(observer.error)
                attempt.accounting.stream_outcome = "image_error"
            elif observer.completed:
                attempt.status = "success"
                attempt.accounting.stream_outcome = "success"
                assert attempt.account is not None
                await proxy._load_balancer.record_success(attempt.account)
            else:
                attempt.error_code = "stream_incomplete"
                attempt.error_message = "Native image stream ended before a completed event"
                attempt.accounting.stream_outcome = "stream_incomplete"
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await upstream.chunks.aclose()
                finally:
                    await self._finish_native_image_attempt(attempt, api_key, client_fields, client_ip)

    async def _finish_native_image_attempt(
        self,
        attempt: _NativeImageAttempt,
        api_key: ApiKeyData | None,
        client_fields: tuple[str | None, str | None, str | None],
        client_ip: str | None,
    ) -> None:
        proxy = cast(_NativeImageServiceProtocol, self)
        with anyio.CancelScope(shield=True):
            try:
                if attempt.lease is not None:
                    await proxy._load_balancer.release_account_lease(attempt.lease)
            finally:
                await self._write_native_image_log(attempt, api_key, client_fields, client_ip)

    async def _write_native_image_log(
        self,
        attempt: _NativeImageAttempt,
        api_key: ApiKeyData | None,
        client_fields: tuple[str | None, str | None, str | None],
        client_ip: str | None,
    ) -> None:
        proxy = cast(_NativeImageServiceProtocol, self)
        useragent, useragent_group, conversation_id = client_fields
        usage = attempt.accounting.usage
        trace = attempt.route_trace
        await proxy._write_request_log(
            account_id=attempt.account.id if attempt.account is not None else None,
            api_key=api_key,
            request_id=attempt.request_id,
            model=attempt.accounting.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            latency_ms=int((clock_for(self).monotonic() - attempt.started_at) * 1000),
            status=attempt.status,
            error_code=attempt.error_code if attempt.status != "success" else None,
            error_message=attempt.error_message if attempt.status != "success" else None,
            transport=_REQUEST_TRANSPORT_HTTP,
            failure_phase=attempt.failure.failure_phase,
            failure_detail=attempt.failure.failure_detail,
            failure_exception_type=attempt.failure.failure_exception_type,
            upstream_status_code=(
                attempt.upstream_status if attempt.upstream_status is not None else attempt.failure.upstream_status_code
            ),
            upstream_error_code=attempt.failure.upstream_error_code,
            bridge_stage=attempt.failure.bridge_stage,
            upstream_proxy_route_mode=trace.mode,
            upstream_proxy_pool_id=trace.pool_id,
            upstream_proxy_endpoint_id=trace.endpoint_id,
            upstream_proxy_fallback_used=trace.fallback_used if trace.endpoint_id else None,
            upstream_proxy_fail_closed_reason=attempt.route_fail_closed_reason,
            useragent=useragent,
            useragent_group=useragent_group,
            conversation_id=conversation_id,
            client_ip=client_ip,
        )
