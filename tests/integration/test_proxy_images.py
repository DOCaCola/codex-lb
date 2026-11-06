"""Integration tests for the Images API surfaces.

These exercise ``/v1/images/*`` and the Codex ``/backend-api/codex/images/*``
aliases end-to-end against a fake native image endpoint
(``core_native_image_request``), covering validation, account selection,
native passthrough, streaming, usage settlement and request logging.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator
from typing import Any, cast

import pytest
from httpx import AsyncByteStream
from sqlalchemy import select
from starlette.datastructures import UploadFile
from starlette.responses import JSONResponse

import app.modules.proxy.api as proxy_api_module
import app.modules.proxy.service as proxy_module
from app.core.clients.proxy import NativeImageStream
from app.core.config.settings import Settings
from app.core.exceptions import ProxyModelNotAllowed, ProxyRateLimitError
from app.core.multipart import MultipartPolicy
from app.db.models import ApiKeyUsageReservation, DashboardSettings
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository

pytestmark = pytest.mark.integration


class _NeverReadStream(AsyncByteStream):
    def __init__(self) -> None:
        self.iterated = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        self.iterated = True
        raise AssertionError("request body must not be consumed")
        yield b""  # pragma: no cover


def _encode_jwt(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"header.{body}.sig"


def _make_auth_json(account_id: str, email: str) -> dict:
    payload = {
        "email": email,
        "chatgpt_account_id": account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    return {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access-token",
            "refreshToken": "refresh-token",
            "accountId": account_id,
        },
    }


async def _import_account(async_client, account_id: str, email: str) -> None:
    auth_json = _make_auth_json(account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200


async def _enable_api_key_auth(async_client) -> None:
    response = await async_client.put(
        "/api/settings",
        json={
            "stickyThreadsEnabled": False,
            "preferEarlierResetAccounts": False,
            "totpRequiredOnLogin": False,
            "apiKeyAuthEnabled": True,
        },
    )
    assert response.status_code == 200


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _data_url(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


@pytest.fixture(autouse=True)
def _disable_http_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    app_settings = Settings(
        http_responses_session_bridge_enabled=False,
        proxy_request_budget_seconds=75.0,
        compact_request_budget_seconds=75.0,
        transcription_request_budget_seconds=120.0,
        stream_idle_timeout_seconds=300.0,
        proxy_response_create_limit=64,
    )
    dashboard_settings = DashboardSettings(
        id=1,
        sticky_threads_enabled=False,
        upstream_stream_transport="auto",
        prefer_earlier_reset_accounts=False,
        routing_strategy="usage_weighted",
        openai_cache_affinity_max_age_seconds=300,
        import_without_overwrite=False,
        totp_required_on_login=False,
        api_key_auth_enabled=False,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=3600,
        http_responses_session_bridge_gateway_safe_mode=False,
        sticky_reallocation_budget_threshold_pct=95.0,
    )

    class _SettingsCache:
        async def get(self) -> DashboardSettings:
            return dashboard_settings

    monkeypatch.setattr(proxy_module, "get_settings_cache", lambda: _SettingsCache())
    monkeypatch.setattr(proxy_module, "get_settings", lambda: app_settings)


# ---------------------------------------------------------------------------
# /v1/images/generations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_images_generations_unsupported_model_returns_400(async_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/generations",
            json={"model": "dall-e-3", "prompt": "a red circle"},
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert (
        "images_route_complete route=generations model=invalid stream=false status=400 outcome=invalid_request"
        in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("base", ["/v1", "/backend-api/codex"])
async def test_images_generations_model_policy_rejection_records_route_observability(
    async_client,
    monkeypatch,
    caplog,
    base,
):
    def reject_model_access(*args, **kwargs):
        del args, kwargs
        raise ProxyModelNotAllowed("This API key does not have access to model 'gpt-image-2'")

    monkeypatch.setattr(proxy_api_module, "validate_model_access", reject_model_access)

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            f"{base}/images/generations",
            json={"model": "gpt-image-2", "prompt": "a red circle"},
        )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["type"] == "permission_error"
    assert (
        "images_route_complete route=generations model=gpt-image-2 stream=false status=403 outcome=model_not_allowed"
        in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("base", ["/v1", "/backend-api/codex"])
async def test_images_generations_quota_rejection_records_route_observability(async_client, monkeypatch, caplog, base):
    async def reject_request_limits(*args, **kwargs):
        del args, kwargs
        raise ProxyRateLimitError("API key quota exceeded")

    monkeypatch.setattr(proxy_api_module, "_enforce_request_limits", reject_request_limits)

    with caplog.at_level(logging.INFO, logger="app.modules.proxy.api"):
        response = await async_client.post(
            f"{base}/images/generations",
            json={"model": "gpt-image-2", "prompt": "a red circle"},
        )

    assert response.status_code == 429
    assert (
        "images_route_complete route=generations model=gpt-image-2 stream=false status=429 outcome=rate_limited"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_images_generations_auth_rejection_records_route_observability(async_client, caplog):
    await _enable_api_key_auth(async_client)

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/generations",
            json={"model": "gpt-image-2", "prompt": "a red circle"},
        )

    assert response.status_code == 401
    message = "images_route_complete route=generations model=gpt-image-2 stream=false status=401 outcome=auth_error"
    assert message in caplog.text
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_backend_codex_images_generations_alias_uses_same_validation(async_client):
    response = await async_client.post(
        "/backend-api/codex/images/generations",
        json={"model": "dall-e-3", "prompt": "a red circle"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["param"] == "model"


@pytest.mark.asyncio
async def test_backend_codex_images_generations_alias_auth_rejection_records_route_observability(async_client, caplog):
    await _enable_api_key_auth(async_client)

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/backend-api/codex/images/generations",
            json={"model": "gpt-image-2", "prompt": "a red circle"},
        )

    assert response.status_code == 401
    message = "images_route_complete route=generations model=gpt-image-2 stream=false status=401 outcome=auth_error"
    assert message in caplog.text
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_images_generations_trailing_slash_parity_between_v1_and_codex_alias(async_client):
    # Codex joins `base_url` + "images/generations" without a trailing slash,
    # so only the exact paths are handled. The trailing-slash variants fall
    # through to the SPA catch-all route and must fail identically (405 with
    # the OpenAI error envelope) on the canonical and alias surfaces.
    payload = {"model": "dall-e-3", "prompt": "a red circle"}
    v1_response = await async_client.post("/v1/images/generations/", json=payload)
    alias_response = await async_client.post("/backend-api/codex/images/generations/", json=payload)
    assert v1_response.status_code == 405
    assert alias_response.status_code == 405
    assert v1_response.json()["error"]["type"] == "invalid_request_error"
    assert alias_response.json() == v1_response.json()


@pytest.mark.asyncio
async def test_images_generations_no_accounts_returns_5xx(async_client):
    response = await async_client.post(
        "/v1/images/generations",
        json={"model": "gpt-image-2", "prompt": "a red circle"},
    )
    assert response.status_code in (502, 503)
    body = response.json()
    assert body["error"]["type"] in {"server_error", "invalid_request_error"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type",
    ["multipart/form-data; boundary=never-read", "application/json"],
    ids=["multipart", "wrong-json-content-type"],
)
async def test_v1_images_edits_auth_rejection_does_not_read_body_and_records_once(
    async_client,
    caplog,
    content_type: str,
) -> None:
    await _enable_api_key_auth(async_client)
    stream = _NeverReadStream()

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            content=stream,
            headers={"content-type": content_type},
        )

    assert response.status_code == 401
    assert stream.iterated is False
    message = "images_route_complete route=edits model=unknown stream=false status=401 outcome=auth_error"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_v1_images_edits_compressed_rejection_does_not_read_body_and_records_once(
    async_client,
    caplog,
) -> None:
    stream = _NeverReadStream()

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            content=stream,
            headers={
                "content-type": "multipart/form-data; boundary=never-read",
                "content-encoding": "gzip",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request_error"
    assert stream.iterated is False
    message = "images_route_complete route=edits model=unknown stream=false status=400 outcome=invalid_request"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_v1_images_edits_missing_content_type_retains_openai_validation_and_records_once(
    async_client,
    caplog,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post("/v1/images/edits", content=b"not multipart")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_request_error"
    assert error["type"] == "invalid_request_error"
    assert error["param"] == "prompt"
    message = "images_route_complete route=edits model=unknown stream=false status=400 outcome=invalid_request"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_v1_images_edits_preserves_mixed_image_order_and_closes_spools_before_pipeline(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_uploads: list[UploadFile] = []
    original_close = UploadFile.close
    captured: dict[str, object] = {}

    async def record_close(upload: UploadFile) -> None:
        await original_close(upload)
        closed_uploads.append(upload)

    async def fake_public_image_response(*_args: object, **kwargs: object) -> JSONResponse:
        assert len(closed_uploads) == 3
        assert all(upload.file.closed for upload in closed_uploads)
        captured.update(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr(UploadFile, "close", record_close)
    monkeypatch.setattr(proxy_api_module, "public_image_response", fake_public_image_response)

    response = await async_client.post(
        "/v1/images/edits",
        files=[
            ("image[]", ("first.png", b"first", "image/png")),
            ("prompt", (None, "keep order")),
            ("image", ("second.webp", b"second", "image/webp")),
            ("mask", ("mask.png", b"mask", "image/png")),
        ],
    )

    assert response.status_code == 200
    body = cast(dict[str, object], captured["body"])
    assert body["images"] == [
        {"image_url": _data_url(b"first", "image/png")},
        {"image_url": _data_url(b"second", "image/webp")},
    ]
    assert body["mask"] == {"image_url": _data_url(b"mask", "image/png")}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("files", "expected_param"),
    [
        (
            [("image", (f"{index}.png", b"x", "image/png")) for index in range(17)]
            + [("prompt", (None, "too many images"))],
            "image",
        ),
        (
            [
                ("image", ("image.png", b"x", "image/png")),
                ("mask", ("first-mask.png", b"x", "image/png")),
                ("mask", ("second-mask.png", b"x", "image/png")),
                ("prompt", (None, "too many masks")),
            ],
            "mask",
        ),
        (
            [
                ("image", ("image.png", b"x", "image/png")),
                ("attachment", ("unknown.bin", b"x", "application/octet-stream")),
                ("prompt", (None, "unknown file")),
            ],
            "attachment",
        ),
    ],
    ids=["combined-image-count", "mask-count", "unknown-file-field"],
)
async def test_v1_images_edits_rejects_invalid_file_shapes_before_pipeline(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
    files: list[tuple[str, tuple[str | None, bytes | str, str] | tuple[None, str]]],
    expected_param: str,
) -> None:
    async def fail_public_image_response(*_args: object, **_kwargs: object) -> JSONResponse:
        raise AssertionError("invalid file shape must not reach image pipeline")

    monkeypatch.setattr(proxy_api_module, "public_image_response", fail_public_image_response)

    response = await async_client.post("/v1/images/edits", files=files)

    assert response.status_code == 400
    assert response.json()["error"]["param"] == expected_param


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image", "mask", "expected_param"),
    [
        (b"12345", None, "image"),
        (b"1234", b"123", "mask"),
    ],
    ids=["per-file", "aggregate"],
)
async def test_v1_images_edits_binary_limits_return_one_413_without_pipeline_work(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
    image: bytes,
    mask: bytes | None,
    expected_param: str,
) -> None:
    monkeypatch.setattr(
        proxy_api_module,
        "IMAGE_EDITS_MULTIPART_POLICY",
        MultipartPolicy(
            max_body_bytes=4096,
            max_file_bytes=4,
            max_aggregate_file_bytes=6,
            max_files=17,
            max_fields=32,
            max_text_part_bytes=32,
        ),
    )

    async def fail_public_image_response(*_args: object, **_kwargs: object) -> JSONResponse:
        raise AssertionError("oversized upload must not reach image pipeline")

    monkeypatch.setattr(proxy_api_module, "public_image_response", fail_public_image_response)
    files: list[tuple[str, tuple[str | None, bytes | str, str] | tuple[None, str]]] = [
        ("image", ("image.png", image, "image/png")),
        ("prompt", (None, "bounded")),
    ]
    if mask is not None:
        files.append(("mask", ("mask.png", mask, "image/png")))

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post("/v1/images/edits", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "payload_too_large"
    assert body["error"]["param"] == expected_param
    message = "images_route_complete route=edits model=unknown stream=false status=413 outcome=invalid_request"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_v1_images_edits_allows_exact_small_binary_policy_boundary(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proxy_api_module,
        "IMAGE_EDITS_MULTIPART_POLICY",
        MultipartPolicy(
            max_body_bytes=4096,
            max_file_bytes=4,
            max_aggregate_file_bytes=6,
            max_files=17,
            max_fields=32,
            max_text_part_bytes=32,
        ),
    )
    captured: dict[str, object] = {}

    async def fake_public_image_response(*_args: object, **kwargs: object) -> JSONResponse:
        captured.update(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr(proxy_api_module, "public_image_response", fake_public_image_response)

    response = await async_client.post(
        "/v1/images/edits",
        files=[
            ("image", ("image.png", b"1234", "image/png")),
            ("mask", ("mask.png", b"12", "image/png")),
            ("prompt", (None, "bounded")),
        ],
    )

    assert response.status_code == 200
    body = cast(dict[str, object], captured["body"])
    assert body["images"] == [{"image_url": _data_url(b"1234", "image/png")}]
    assert body["mask"] == {"image_url": _data_url(b"12", "image/png")}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("policy", "prompt"),
    [
        (
            MultipartPolicy(
                max_body_bytes=64,
                max_file_bytes=16,
                max_aggregate_file_bytes=16,
                max_files=17,
                max_fields=32,
                max_text_part_bytes=32,
            ),
            "body",
        ),
        (
            MultipartPolicy(
                max_body_bytes=4096,
                max_file_bytes=16,
                max_aggregate_file_bytes=16,
                max_files=17,
                max_fields=32,
                max_text_part_bytes=4,
            ),
            "12345",
        ),
    ],
    ids=["body", "text-part"],
)
async def test_v1_images_edits_body_and_text_limits_reject_before_pipeline(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
    policy: MultipartPolicy,
    prompt: str,
) -> None:
    monkeypatch.setattr(proxy_api_module, "IMAGE_EDITS_MULTIPART_POLICY", policy)

    async def fail_public_image_response(*_args: object, **_kwargs: object) -> JSONResponse:
        raise AssertionError("oversized multipart input must not reach image pipeline")

    monkeypatch.setattr(proxy_api_module, "public_image_response", fail_public_image_response)

    response = await async_client.post(
        "/v1/images/edits",
        files=[
            ("image", ("image.png", b"1234", "image/png")),
            ("prompt", (None, prompt)),
        ],
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image", "mask", "expected_param"),
    [(b"", None, "image"), (b"image", b"", "mask")],
    ids=["empty-image", "empty-mask"],
)
async def test_v1_images_edits_rejects_empty_binary_parts_before_pipeline(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
    image: bytes,
    mask: bytes | None,
    expected_param: str,
) -> None:
    async def fail_public_image_response(*_args: object, **_kwargs: object) -> JSONResponse:
        raise AssertionError("empty multipart input must not reach image pipeline")

    monkeypatch.setattr(proxy_api_module, "public_image_response", fail_public_image_response)
    files: list[tuple[str, tuple[str | None, bytes | str, str] | tuple[None, str]]] = [
        ("image", ("image.png", image, "image/png")),
        ("prompt", (None, "empty part")),
    ]
    if mask is not None:
        files.append(("mask", ("mask.png", mask, "image/png")))

    response = await async_client.post("/v1/images/edits", files=files)

    assert response.status_code == 400
    assert response.json()["error"]["param"] == expected_param


@pytest.mark.asyncio
async def test_v1_images_edits_malformed_multipart_records_one_invalid_request(
    async_client,
    caplog,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            content=b"not multipart",
            headers={"content-type": "multipart/form-data; boundary=broken"},
        )

    assert response.status_code == 400
    message = "images_route_complete route=edits model=unknown stream=false status=400 outcome=invalid_request"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_backend_codex_images_edits_requires_native_image_data_urls(async_client, caplog):
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/backend-api/codex/images/edits",
            json={"model": "gpt-image-2", "prompt": "make it green", "images": []},
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["param"] == "images"
    assert (
        "images_route_complete route=edits model=gpt-image-2 stream=false status=400 outcome=invalid_request"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_backend_codex_images_edits_alias_auth_rejection_records_route_observability(async_client, caplog):
    await _enable_api_key_auth(async_client)

    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/backend-api/codex/images/edits",
            json={
                "model": "gpt-image-2",
                "prompt": "make it green",
                "images": [{"image_url": "data:image/png;base64,aGVsbG8="}],
            },
        )

    assert response.status_code == 401
    message = "images_route_complete route=edits model=gpt-image-2 stream=false status=401 outcome=auth_error"
    assert message in caplog.text
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_images_edits_trailing_slash_parity_between_v1_and_codex_alias(async_client):
    # Codex joins `base_url` + "images/edits" without a trailing slash, so
    # only the exact paths are handled. The trailing-slash variants fall
    # through to the SPA catch-all route and must fail identically (405 with
    # the OpenAI error envelope) on the canonical and alias surfaces.
    payload = {"model": "gpt-image-2", "prompt": "make it green", "images": []}
    v1_response = await async_client.post("/v1/images/edits/", json=payload)
    alias_response = await async_client.post("/backend-api/codex/images/edits/", json=payload)
    assert v1_response.status_code == 405
    assert alias_response.status_code == 405
    assert v1_response.json()["error"]["type"] == "invalid_request_error"
    assert alias_response.json() == v1_response.json()


@pytest.mark.asyncio
async def test_backend_codex_images_edits_invalid_utf8_returns_400(async_client, caplog):
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/backend-api/codex/images/edits",
            content=b"\xff",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["param"] == "prompt"
    assert (
        "images_route_complete route=edits model=unknown stream=false status=400 outcome=invalid_request" in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["generations", "edits"])
@pytest.mark.parametrize("upstream_status", [200, 400, 401, 429, 502, 307])
async def test_native_images_preserve_status_body_and_do_not_replay(
    async_client, monkeypatch, operation, upstream_status
):
    await _import_account(async_client, "native-errors", "native-errors@example.com")
    calls = []
    raw_response = b'{"created":1,"data":[{"b64_json":"IMAGE"}],"error":{"code":"native_error","detail":"kept"}}'

    async def fake_native(operation, **kwargs):
        calls.append((operation, kwargs))
        return proxy_module.CodexControlResponse(
            status_code=upstream_status,
            body=raw_response,
            headers={"content-type": "application/json", "retry-after": "17", "set-cookie": "secret=value"},
        )

    async def fresh(self, account, **kwargs):
        return account

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    monkeypatch.setattr(proxy_module.ProxyService, "_ensure_fresh_with_budget", fresh)
    payload = {"model": "gpt-image-2", "prompt": "hello", "images": [{"image_url": "data:image/png;base64,aA=="}]}
    response = await async_client.post(f"/backend-api/codex/images/{operation}", json=payload)
    assert response.status_code == upstream_status, response.text
    assert response.content == raw_response
    assert "set-cookie" not in response.headers
    assert response.headers["retry-after"] == "17"
    assert len(calls) == 1
    assert calls[0][0] == operation
    assert json.loads(calls[0][1]["payload"]) == payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result", ["success", "zero_usage", "missing_usage", "invalid_usage", "error", "transport", "cancel"]
)
@pytest.mark.parametrize("operation", ["generations", "edits"])
@pytest.mark.parametrize("all_models", [True, False])
async def test_native_images_release_capacity_and_settle_scoped_key(
    async_client, monkeypatch, result, operation, all_models
):
    from app.core.clients.proxy import ProxyResponseError
    from app.db.models import Account

    await _import_account(async_client, "native-scope", "native-scope@example.com")
    await _import_account(async_client, "not-assigned", "not-assigned@example.com")
    async with SessionLocal() as session:
        account = (
            await session.execute(select(Account).where(Account.chatgpt_account_id == "native-scope"))
        ).scalar_one()
        assigned_id = account.id
        account.all_models = all_models
        account.selected_models = []
        await session.commit()
    await _enable_api_key_auth(async_client)
    created = await async_client.post(
        "/api/api-keys/",
        json={
            "name": "native-limited",
            "allowedModels": ["gpt-image-2", "openrouter/z-ai/glm-5.3-flash"],
            "limits": [
                {"limitType": "total_tokens", "limitWindow": "weekly", "maxValue": 1000000},
                {"limitType": "cost_usd", "limitWindow": "weekly", "maxValue": 1000000},
            ],
        },
    )
    assert created.status_code == 200, created.text
    key = created.json()
    scoped = await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [assigned_id]})
    assert scoped.status_code == 200, scoped.text
    services = []
    calls = []
    selection_models = []
    original_select = proxy_module.ProxyService._select_account_with_budget

    async def select_account(self, *args, **kwargs):
        services.append(self)
        selection_models.append(kwargs.get("model"))
        return await original_select(self, *args, **kwargs)

    async def fresh(self, account, **kwargs):
        return account

    async def native(operation, **kwargs):
        calls.append(kwargs["account_id"])
        if result == "cancel":
            raise asyncio.CancelledError()
        if result == "transport":
            raise ProxyResponseError(502, {"error": {"code": "upstream_unavailable", "message": "connection lost"}})
        status = 429 if result == "error" else 200
        body = {"created": 1, "data": [{"b64_json": "image"}]}
        if result != "missing_usage":
            body["usage"] = {
                "input_tokens": "invalid" if result == "invalid_usage" else 0 if result == "zero_usage" else 3,
                "output_tokens": 0 if result == "zero_usage" else 7,
                "input_tokens_details": {"cached_tokens": 0 if result == "zero_usage" else 2},
            }
        return proxy_module.CodexControlResponse(
            status,
            json.dumps(body).encode(),
            {"content-type": "application/json"},
        )

    monkeypatch.setattr(proxy_module.ProxyService, "_select_account_with_budget", select_account)
    monkeypatch.setattr(proxy_module.ProxyService, "_ensure_fresh_with_budget", fresh)
    monkeypatch.setattr(proxy_module, "core_native_image_request", native)
    request = async_client.post(
        f"/backend-api/codex/images/{operation}",
        headers={"Authorization": f"Bearer {key['key']}"},
        json={"model": "gpt-image-2", "prompt": "hello", "images": [{"image_url": "data:image/png;base64,aA=="}]},
    )
    if result == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await request
    else:
        response = await request
        assert response.status_code == {"error": 429, "transport": 502}.get(result, 200), response.text
    assert calls == ["native-scope"]
    assert selection_models == [None]
    assert await services[0].drain_persistence_tasks(timeout_seconds=5)
    pressure = await services[0]._load_balancer.account_pressure_snapshot(assigned_id)
    assert pressure == (0, 0, 0.0)
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(ApiKeyUsageReservation).where(
                        ApiKeyUsageReservation.api_key_id == key["id"],
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].status == ("finalized" if result in {"success", "zero_usage"} else "released")
        limits = await ApiKeysRepository(session).get_limits_by_key(key["id"])
        values = {limit.limit_type.value: limit.current_value for limit in limits}
        assert values["total_tokens"] == (10 if result == "success" else 0)
        assert values["cost_usd"] == (219 if result == "success" else 0)

    logs = await async_client.get(f"/api/request-logs?accountId={assigned_id}")
    assert logs.status_code == 200, logs.text
    entries = [entry for entry in logs.json()["requests"] if entry["model"] == "gpt-image-2"]
    assert len(entries) == 1
    entry = entries[0]
    absent = 0 if result == "zero_usage" else None
    assert entry["inputTokens"] == (3 if result == "success" else absent)
    assert entry["outputTokens"] == (7 if result == "success" else absent)
    assert entry["cachedInputTokens"] == (2 if result == "success" else absent)
    if result == "success":
        assert entry["costUsd"] == pytest.approx(0.000219)
    else:
        assert entry["costUsd"] == absent


@pytest.mark.asyncio
async def test_native_images_do_not_bypass_account_admission(async_client, monkeypatch):
    from app.modules.proxy.load_balancer import AccountSelection

    async def denied(self, *args, **kwargs):
        return AccountSelection(account=None, error_message="quota unavailable", error_code="no_accounts")

    async def forbidden(*args, **kwargs):
        pytest.fail("native images must not bypass admission or try a different backend")

    monkeypatch.setattr(proxy_module.ProxyService, "_select_account_with_budget_compatible", denied)
    monkeypatch.setattr(proxy_module, "core_native_image_request", forbidden)
    response = await async_client.post(
        "/backend-api/codex/images/generations",
        json={"model": "gpt-image-2", "prompt": "hello"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "no_accounts"


@pytest.mark.asyncio
@pytest.mark.parametrize("image_url", ["data:image/png;base64,aW1hZ2U=", "https://images.example/reference.png"])
async def test_backend_codex_images_edits_json_data_urls_round_trip(async_client, monkeypatch, image_url):
    from app.modules.proxy import native_image_usage

    await _import_account(async_client, "acc_images_edit_codex", "img-edit-codex@example.com")
    captured = {}
    services = []
    usage_parses = []
    original_log = proxy_module.ProxyService._write_request_log
    original_parse = native_image_usage.reported_image_usage

    async def record_log(self, **kwargs):
        services.append(self)
        await original_log(self, **kwargs)

    def parse_usage(response):
        usage_parses.append(response)
        return original_parse(response)

    monkeypatch.setattr(proxy_module.ProxyService, "_write_request_log", record_log)
    monkeypatch.setattr(native_image_usage, "reported_image_usage", parse_usage)

    async def fake_native(operation, **kwargs):
        captured.update(kwargs)
        captured["operation"] = operation
        return proxy_module.CodexControlResponse(
            status_code=200,
            body=(
                b'{"created":1,"data":[{"b64_json":"EDITED_B64","generation_id":"gen-native"}],'
                b'"background":"opaque","usage":{"input_tokens":3,"output_tokens":7}}'
            ),
            headers={"content-type": "application/json", "x-codex-imagegen-request-id": "native-id"},
        )

    async def fake_ensure_fresh(self, account, **kwargs):
        return account

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    monkeypatch.setattr(proxy_module.ProxyService, "_ensure_fresh_with_budget", fake_ensure_fresh)
    payload = {
        "model": "gpt-image-2",
        "prompt": "make it green",
        "images": [{"image_url": image_url}],
        "future_native_field": {"keep": True},
    }
    response = await async_client.post("/backend-api/codex/images/edits", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == [{"b64_json": "EDITED_B64", "generation_id": "gen-native"}]
    assert response.json()["background"] == "opaque"
    assert response.headers["x-codex-imagegen-request-id"] == "native-id"
    assert captured["operation"] == "edits"
    assert json.loads(captured["payload"]) == payload
    assert captured["access_token"] == "access-token"
    assert captured["account_id"] == "acc_images_edit_codex"
    assert len(usage_parses) == 1
    assert len(services) == 1
    assert await services[0].drain_persistence_tasks(timeout_seconds=5)
    assert response.content == usage_parses[0].body
    logs = await async_client.get("/api/request-logs")
    entries = [entry for entry in logs.json()["requests"] if entry["model"] == "gpt-image-2"]
    assert len(entries) == 1
    assert entries[0]["inputTokens"] == 3
    assert entries[0]["outputTokens"] == 7
    assert entries[0]["costUsd"] == pytest.approx(0.000225)


@pytest.mark.asyncio
async def test_images_edits_uses_route_started_at_after_file_reads(async_client, monkeypatch):
    import app.core.handlers.exceptions as exceptions_module

    captured: dict[str, Any] = {}

    async def fake_public_image_response(*_args, **kwargs):
        captured.update(kwargs)
        return JSONResponse({"ok": True})

    monkeypatch.setattr(exceptions_module.time, "perf_counter", lambda: 123.456)
    monkeypatch.setattr(proxy_api_module, "public_image_response", fake_public_image_response)

    image_bytes = b"\x89PNG\r\n\x1a\n"
    response = await async_client.post(
        "/v1/images/edits",
        data={
            "model": "gpt-image-2",
            "prompt": "hi",
        },
        files={"image": ("source.png", image_bytes, "image/png")},
    )

    assert response.status_code == 200
    assert captured["started_at"] == 123.456
    assert captured["body"]["images"] == [{"image_url": _data_url(image_bytes, "image/png")}]


@pytest.mark.asyncio
async def test_images_edits_unsupported_model(async_client, caplog):
    image_bytes = b"\x89PNG\r\n\x1a\n"
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            data={
                "model": "bad-model-for-observability-cardinality",
                "prompt": "hi",
            },
            files={"image": ("source.png", image_bytes, "image/png")},
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert (
        "images_route_complete route=edits model=invalid stream=false status=400 outcome=invalid_request" in caplog.text
    )


@pytest.mark.asyncio
async def test_images_edits_missing_image_records_route_observability(async_client, caplog):
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            files=[
                ("model", (None, "gpt-image-2")),
                ("prompt", (None, "hi")),
            ],
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["param"] == "image"
    assert (
        "images_route_complete route=edits model=gpt-image-2 stream=false status=400 outcome=invalid_request"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_images_edits_validation_error_records_supplied_model(async_client, caplog):
    image_bytes = b"\x89PNG\r\n\x1a\n"
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            data={"model": "gpt-image-2"},
            files={"image": ("source.png", image_bytes, "image/png")},
        )

    assert response.status_code == 400
    assert (
        "images_route_complete route=edits model=gpt-image-2 stream=false status=400 outcome=invalid_request"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_images_edits_quota_rejection_records_route_observability(async_client, monkeypatch, caplog):
    async def reject_request_limits(*args, **kwargs):
        del args, kwargs
        raise ProxyRateLimitError("API key quota exceeded")

    monkeypatch.setattr(proxy_api_module, "_enforce_request_limits", reject_request_limits)

    image_bytes = b"\x89PNG\r\n\x1a\n"
    with caplog.at_level(logging.WARNING, logger="app.modules.proxy.api"):
        response = await async_client.post(
            "/v1/images/edits",
            data={
                "model": "gpt-image-2",
                "prompt": "hi",
            },
            files={"image": ("source.png", image_bytes, "image/png")},
        )

    assert response.status_code == 429
    assert (
        "images_route_complete route=edits model=gpt-image-2 stream=false status=429 outcome=rate_limited"
        in caplog.text
    )


# ---------------------------------------------------------------------------
# /v1/images/variations is explicitly not supported.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_images_variations_returns_404(async_client):
    response = await async_client.post(
        "/v1/images/variations",
        json={"model": "gpt-image-2", "prompt": "no"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found_error"


# ---------------------------------------------------------------------------
# Public /v1 native forwarding.
# ---------------------------------------------------------------------------


def _native_image_stream(
    chunks: list[bytes],
    *,
    failure: Exception | None = None,
    closed: list[bool] | None = None,
) -> NativeImageStream:
    async def produce() -> AsyncIterator[bytes]:
        try:
            for chunk in chunks:
                yield chunk
            if failure is not None:
                raise failure
        finally:
            if closed is not None:
                closed.append(True)

    return NativeImageStream(
        status_code=200,
        headers={"content-type": "text/event-stream", "x-codex-imagegen-request-id": "stream-id"},
        chunks=cast(Any, produce()),
    )


def _event(name: str, payload: dict[str, object]) -> bytes:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode()


async def _image_log_entries(async_client, service_holder: list[Any]) -> list[dict[str, Any]]:
    assert await service_holder[0].drain_persistence_tasks(timeout_seconds=5)
    logs = await async_client.get("/api/request-logs")
    assert logs.status_code == 200, logs.text
    return [entry for entry in logs.json()["requests"] if str(entry["model"]).startswith("gpt-image-")]


def _record_services(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    services: list[Any] = []
    original_log = proxy_module.ProxyService._write_request_log

    async def record_log(self, **kwargs):
        services.append(self)
        await original_log(self, **kwargs)

    async def fresh(self, account, **kwargs):
        return account

    monkeypatch.setattr(proxy_module.ProxyService, "_write_request_log", record_log)
    monkeypatch.setattr(proxy_module.ProxyService, "_ensure_fresh_with_budget", fresh)
    return services


@pytest.mark.asyncio
async def test_v1_images_generations_forwards_native_request_unchanged(async_client, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.modules.proxy.api")
    await _import_account(async_client, "v1-native", "v1-native@example.com")
    services = _record_services(monkeypatch)
    captured: dict[str, Any] = {}
    raw_response = (
        b'{"created":1,"data":[{"b64_json":"IMG"},{"b64_json":"IMG2"}],"background":"transparent",'
        b'"usage":{"input_tokens":3,"output_tokens":7}}'
    )

    async def fake_native(operation, **kwargs):
        captured["operation"] = operation
        captured.update(kwargs)
        return proxy_module.CodexControlResponse(200, raw_response, {"content-type": "application/json"})

    async def rate_limit_headers(self):
        return {"x-codex-primary-used-percent": "12"}

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    monkeypatch.setattr(proxy_module.ProxyService, "rate_limit_headers", rate_limit_headers)
    payload = {
        "model": "gpt-image-2.6-flare",
        "prompt": "a lighthouse",
        "n": 2,
        "quality": "xhigh",
        "complexity": "high",
        "background": "transparent",
        "size": "3000x1000",
    }
    response = await async_client.post("/v1/images/generations", json=payload)

    assert response.status_code == 200, response.text
    assert response.content == raw_response
    assert response.headers["x-codex-primary-used-percent"] == "12"
    assert captured["operation"] == "generations"
    assert json.loads(captured["payload"]) == payload
    entries = await _image_log_entries(async_client, services)
    assert [(entry["model"], entry["inputTokens"], entry["outputTokens"]) for entry in entries] == [
        ("gpt-image-2.6-flare", 3, 7)
    ]
    message = (
        "images_route_complete route=generations model=gpt-image-2.6-flare stream=false status=200 outcome=success"
    )
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
async def test_v1_images_generations_applies_default_model(async_client, monkeypatch):
    await _import_account(async_client, "v1-default", "v1-default@example.com")
    _record_services(monkeypatch)
    captured: dict[str, Any] = {}

    async def fake_native(operation, **kwargs):
        captured.update(kwargs)
        return proxy_module.CodexControlResponse(200, b'{"created":1,"data":[]}', {"content-type": "application/json"})

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    response = await async_client.post("/v1/images/generations", json={"prompt": "a lighthouse"})

    assert response.status_code == 200, response.text
    assert json.loads(captured["payload"]) == {"prompt": "a lighthouse", "model": "gpt-image-2"}


@pytest.mark.asyncio
async def test_v1_images_generations_streams_native_events_and_settles_usage(async_client, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.modules.proxy.api")
    await _import_account(async_client, "v1-stream", "v1-stream@example.com")
    services = _record_services(monkeypatch)
    closed: list[bool] = []
    partial = _event("image_generation.partial_image", {"type": "image_generation.partial_image", "b64_json": "P"})
    completed = _event(
        "image_generation.completed",
        {"type": "image_generation.completed", "b64_json": "F", "usage": {"input_tokens": 3, "output_tokens": 7}},
    )
    # Split the completed event across chunks: forwarding must not wait for
    # whole events.
    chunks = [partial, completed[:20], completed[20:]]

    async def fake_native(operation, **kwargs):
        return _native_image_stream(chunks, closed=closed)

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    response = await async_client.post(
        "/v1/images/generations",
        json={"model": "gpt-image-2", "prompt": "a lighthouse", "stream": True, "partial_images": 1},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-codex-imagegen-request-id"] == "stream-id"
    assert response.content == b"".join(chunks)
    assert closed == [True]
    entries = await _image_log_entries(async_client, services)
    assert len(entries) == 1
    assert entries[0]["status"] == "ok"
    assert (entries[0]["inputTokens"], entries[0]["outputTokens"]) == (3, 7)
    message = "images_route_complete route=generations model=gpt-image-2 stream=true status=200 outcome=success"
    assert caplog.text.count(message) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("chunks", "error_code", "outcome"),
    [
        (
            [_event("error", {"type": "error", "error": {"code": "moderation_blocked", "message": "blocked"}})],
            "moderation_blocked",
            "image_error",
        ),
        (
            [_event("image_generation.partial_image", {"type": "image_generation.partial_image", "b64_json": "P"})],
            "stream_incomplete",
            "stream_incomplete",
        ),
    ],
    ids=["error-event", "incomplete"],
)
async def test_v1_images_stream_failures_are_logged_as_errors(
    async_client, monkeypatch, caplog, chunks, error_code, outcome
):
    caplog.set_level(logging.INFO, logger="app.modules.proxy.api")
    await _import_account(async_client, "v1-stream-error", "v1-stream-error@example.com")
    services = _record_services(monkeypatch)

    async def fake_native(operation, **kwargs):
        return _native_image_stream(chunks)

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    response = await async_client.post(
        "/v1/images/generations",
        json={"model": "gpt-image-2", "prompt": "a lighthouse", "stream": True},
    )

    assert response.status_code == 200
    assert response.content == b"".join(chunks)
    entries = await _image_log_entries(async_client, services)
    assert [(entry["status"], entry["errorCode"]) for entry in entries] == [("error", error_code)]
    assert f"stream=true status=200 outcome={outcome}" in caplog.text


@pytest.mark.asyncio
async def test_v1_images_stream_transport_failure_between_events_emits_error_event(async_client, monkeypatch):
    from app.core.clients.proxy import ProxyResponseError

    await _import_account(async_client, "v1-stream-drop", "v1-stream-drop@example.com")
    services = _record_services(monkeypatch)
    partial = _event("image_generation.partial_image", {"type": "image_generation.partial_image", "b64_json": "P"})
    failure = ProxyResponseError(502, {"error": {"code": "upstream_unavailable", "message": "connection lost"}})

    async def fake_native(operation, **kwargs):
        return _native_image_stream([partial], failure=failure)

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    response = await async_client.post(
        "/v1/images/generations",
        json={"model": "gpt-image-2", "prompt": "a lighthouse", "stream": True},
    )

    assert response.status_code == 200
    assert response.content.startswith(partial)
    tail = response.content[len(partial) :].decode()
    assert tail.startswith("event: error\n")
    event = json.loads(tail.split("data: ", 1)[1])
    assert event == {"type": "error", "error": {"code": "upstream_unavailable", "message": "connection lost"}}
    entries = await _image_log_entries(async_client, services)
    assert [(entry["status"], entry["errorCode"]) for entry in entries] == [("error", "upstream_unavailable")]


@pytest.mark.asyncio
async def test_v1_images_edits_multipart_becomes_native_json(async_client, monkeypatch):
    await _import_account(async_client, "v1-edit-native", "v1-edit-native@example.com")
    _record_services(monkeypatch)
    captured: dict[str, Any] = {}

    async def fake_native(operation, **kwargs):
        captured["operation"] = operation
        captured.update(kwargs)
        return proxy_module.CodexControlResponse(200, b'{"created":1,"data":[]}', {"content-type": "application/json"})

    monkeypatch.setattr(proxy_module, "core_native_image_request", fake_native)
    response = await async_client.post(
        "/v1/images/edits",
        files=[
            ("prompt", (None, "make it green")),
            ("image[]", ("first.png", b"first", "image/png")),
            ("n", (None, "2")),
            ("stream", (None, "false")),
            ("image", ("second.webp", b"second", "image/webp")),
            ("quality", (None, "max")),
            ("mask", ("mask.png", b"mask", "image/png")),
        ],
    )

    assert response.status_code == 200, response.text
    assert captured["operation"] == "edits"
    assert json.loads(captured["payload"]) == {
        "prompt": "make it green",
        "n": 2,
        "stream": False,
        "quality": "max",
        "model": "gpt-image-2",
        "images": [
            {"image_url": _data_url(b"first", "image/png")},
            {"image_url": _data_url(b"second", "image/webp")},
        ],
        "mask": {"image_url": _data_url(b"mask", "image/png")},
    }
