import json

import pytest
from aiohttp import web
from sqlalchemy import select

from app.db.models import ModelSource, RequestLog
from app.db.session import SessionLocal
from tests.integration.model_source_helpers import stub_source_upstreams
from tests.integration.test_openrouter_accounts import provider

__all__ = ["provider"]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("status", [400, 401, 403])
@pytest.mark.parametrize("stream", [True, False])
@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_provider_reason_reaches_client_and_log(async_client, provider, status, stream, path):
    secret = "sk-or-v1-synthetic-test-key"
    calls = 0

    async def upstream(request):
        nonlocal calls
        calls += 1
        return web.json_response(
            {
                "error": {
                    "code": status,
                    "message": "Provider returned error",
                    "metadata": {
                        "provider_name": "Example",
                        "raw": json.dumps(
                            {"error": {"message": "Unsupported parameter " + secret, "param": "reasoning"}}
                        ),
                        "request": "private prompt",
                    },
                }
            },
            status=status,
            headers={"Retry-After": "7"},
        )

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "Diagnostics", "apiKey": secret})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            source.base_url = url
            await session.commit()
        response = await async_client.post(
            path, json={"model": "openrouter/vendor/test", "input": "Hi", "stream": stream}
        )
        assert response.status_code == (502 if status == 401 else status), response.text
        assert response.headers["retry-after"] == "7"
        if status == 401:
            assert "model_source_credentials_error" in response.text
            assert "Unsupported parameter" not in response.text
        else:
            assert "Unsupported parameter" in response.text
            assert "provider: Example" in response.text
        assert secret not in response.text and "private prompt" not in response.text
        assert calls == 1
        async with SessionLocal() as session:
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log is not None
            assert log.upstream_status_code == status
            assert log.error_code == ("model_source_credentials_error" if status == 401 else str(status))
            if status != 401:
                assert "Unsupported parameter" in log.error_message
                assert "provider: Example" in log.error_message
            assert secret not in log.error_message


@pytest.mark.parametrize("body", [b"not JSON private data", b"x" * 70000, b"[" * 10000 + b"]" * 10000])
async def test_unusable_body_preserves_status_without_raw_data(async_client, provider, body):
    async def upstream(request):
        return web.Response(status=403, body=body)

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "Bounded", "apiKey": "synthetic"})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            source.base_url = url
            await session.commit()
        response = await async_client.post(
            "/v1/responses", json={"model": "openrouter/vendor/test", "input": "Hi", "stream": True}
        )
        assert response.status_code == 403, response.text
        assert len(response.content) < 1024
        assert "private data" not in response.text
        assert "credentials" not in response.text
