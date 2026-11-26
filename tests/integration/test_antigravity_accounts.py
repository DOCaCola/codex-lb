import json
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from app.db.models import AntigravityClientBuild
from app.db.session import SessionLocal
from app.modules.antigravity import oauth
from app.modules.antigravity.client import CloudCodeClient, LoadCodeAssist
from app.modules.antigravity.constants import GO_SKIP_AUTO_HEADERS, SKIP_SIGNATURE
from app.modules.antigravity.schemas import Credentials, UserInfo
from tests.integration.model_source_helpers import _enable_api_key_auth

pytestmark = pytest.mark.integration

GEMINI = "antigravity/gemini-3.8-flash"
CLAUDE = "antigravity/claude-opus-5-5"
USER_AGENT = "antigravity/cli/1.4.10 (aidev_client; os_type=linux; arch=arm64; cl=1009308193; auth_method=consumer)"
# fetchAvailableModels shape of the agy 1.4.10 capture.
CATALOG = {
    "models": {
        "gemini-3.8-flash-low": {
            "displayName": "Gemini 3.8 Flash (Low)",
            "apiProvider": "API_PROVIDER_GOOGLE_GEMINI",
            "maxTokens": 1_048_576,
            "maxOutputTokens": 65_536,
            "supportsThinking": True,
            "model": "MODEL_PLACEHOLDER_M899",
        },
        "gemini-3.8-flash-high": {
            "displayName": "Gemini 3.8 Flash (High)",
            "apiProvider": "API_PROVIDER_GOOGLE_GEMINI",
            "maxTokens": 1_048_576,
            "maxOutputTokens": 65_536,
            "supportsThinking": True,
            "model": "MODEL_PLACEHOLDER_M900",
        },
        "claude-opus-5-5": {
            "displayName": "Claude Opus 5.5",
            "apiProvider": "API_PROVIDER_ANTHROPIC_VERTEX",
            "maxTokens": 200_000,
            "maxOutputTokens": 64_000,
            "supportsThinking": True,
            "model": "MODEL_PLACEHOLDER_M905",
        },
    },
    "agentModelSorts": [
        {"groups": [{"modelIds": ["gemini-3.8-flash-high", "gemini-3.8-flash-low", "claude-opus-5-5"]}]}
    ],
    "defaultAgentModelId": "gemini-3.8-flash-high",
    "tieredModelIds": {"flashLite": ["gemini-3.8-flash-lite"]},
}
QUOTA_EXHAUSTED: dict[str, Any] = {
    "error": {
        "code": 429,
        "status": "RESOURCE_EXHAUSTED",
        "message": "You have exhausted your capacity on this model.",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "QUOTA_EXHAUSTED",
                "domain": "cloudcode-pa.googleapis.com",
            }
        ],
    }
}


def credential_file(token: str) -> dict[str, object]:
    return {"type": "antigravity", "refresh_token": token}


@pytest.fixture
async def pool(async_client, monkeypatch):
    async with SessionLocal() as session:
        session.add(
            AntigravityClientBuild(
                sha512="a" * 128,
                platform="darwin_arm64",
                version="1.4.10",
                changelist="1009308193",
                build_id=None,
                archive_url=None,
                verified_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await session.commit()
    patch = await async_client.patch("/api/antigravity-accounts/version", json={"platform": "linux_arm64"})
    assert patch.status_code == 200, patch.text
    async with SessionLocal() as session:
        build = await session.get(AntigravityClientBuild, "a" * 128)
        assert build is not None
        build.platform = "linux_arm64"
        await session.commit()

    async def refresh(token: str) -> Credentials:
        return Credentials(
            access_token=SecretStr(f"access-{token}"),
            refresh_token=SecretStr(token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    async def userinfo(access_token: str) -> UserInfo:
        subject = access_token.removeprefix("access-").removesuffix("-again")
        return UserInfo(id=f"subject-{subject}", email=f"{subject}@example.com")

    monkeypatch.setattr(oauth, "refresh", refresh)
    monkeypatch.setattr(oauth, "userinfo", userinfo)
    monkeypatch.setattr(
        CloudCodeClient,
        "load_code_assist",
        AsyncMock(
            return_value=LoadCodeAssist.model_validate(
                {"currentTier": {"id": "standard-tier"}, "cloudaicompanionProject": "project-1"}
            )
        ),
    )
    monkeypatch.setattr(CloudCodeClient, "available_models", AsyncMock(return_value=CATALOG))
    monkeypatch.setattr(CloudCodeClient, "quota_summary", AsyncMock(return_value={"quotaSummary": {"groups": []}}))
    ids = []
    for token in ("alpha", "beta"):
        response = await async_client.post(
            "/api/antigravity-accounts/import", json={"name": token, "credentials": credential_file(token)}
        )
        assert response.status_code == 200, response.text
        account = response.json()
        # Google names third-party use as grounds for suspension: the operator opts in per account.
        assert account["isEnabled"] is False
        enabled = await async_client.patch(f"/api/antigravity-accounts/{account['id']}", json={"isEnabled": True})
        assert enabled.status_code == 200, enabled.text
        ids.append(account["id"])
    return ids


HELLO: list[dict[str, Any]] = [
    {"response": {"candidates": [{"content": {"role": "model", "parts": [{"text": "Hello"}]}}]}},
    {
        "response": {
            "candidates": [{"content": {"role": "model", "parts": [{"text": " there"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 3},
            "responseId": "fixture",
        }
    },
]


def install_upstream(
    monkeypatch,
    *,
    rejections: int = 0,
    rejection: dict[str, Any] = QUOTA_EXHAUSTED,
    rejection_status: int = 429,
    rejection_retry_after: str | None = None,
    rounds: list[list[dict[str, Any]]] | None = None,
):
    """Fake streamGenerateContent; each accepted request answers with the next of rounds."""
    from app.modules.antigravity import transport
    from app.modules.model_sources.forwarding import ModelSourceForwardingError

    captured: list[tuple[str, dict[str, Any], dict[str, str]]] = []
    answers = rounds or [HELLO]

    async def open_stream(source, path, payload, **kwargs):
        assert path == transport.STREAM_PATH
        assert kwargs["skip_auto_headers"] is GO_SKIP_AUTO_HEADERS
        captured.append((source.id, payload, kwargs["prepared_headers"]))
        if len(captured) <= rejections:
            raise ModelSourceForwardingError(
                status_code=rejection_status,
                payload=rejection,
                upstream_status_code=rejection_status,
                retry_after=rejection_retry_after,
            )
        lines = answers[min(len(captured) - rejections, len(answers)) - 1]

        async def chunks(_size):
            for line in lines:
                yield f"data: {json.dumps(line)}\n\n".encode()

        response = SimpleNamespace(status=200, headers={}, content=SimpleNamespace(iter_chunked=chunks))
        return AsyncExitStack(), response, None

    monkeypatch.setattr(transport, "_open_source_stream", open_stream)
    return captured


async def ask(async_client, model: str, conversation: str = "conversation-1") -> dict[str, Any]:
    response = await async_client.post(
        "/backend-api/codex/responses",
        json={"model": model, "input": "Hi", "stream": False, "prompt_cache_key": conversation},
        headers={"session_id": conversation},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_responses_reach_antigravity_as_the_native_agent(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch)

    body = await ask(async_client, GEMINI)

    assert body["status"] == "completed"
    assert body["output"][-1]["content"][0]["text"] == "Hello there"
    ((source_id, envelope, headers),) = captured
    assert source_id in pool
    assert headers["User-Agent"] == USER_AGENT
    assert headers["Authorization"].startswith("Bearer access-")
    assert list(envelope) == ["project", "requestId", "request", "model", "userAgent", "requestType"]
    assert (envelope["project"], envelope["userAgent"], envelope["requestType"]) == (
        "project-1",
        "antigravity",
        "agent",
    )
    labels = envelope["request"]["labels"]
    assert labels["model_enum"] == f"MODEL_PLACEHOLDER_M{900 if envelope['model'].endswith('high') else 899}"
    assert labels["used_non_gemini_model"] == "true"
    assert not {"used_claude", "used_claude_conservative"} & set(labels)


async def test_enforced_redirect_routes_to_antigravity(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch)
    source = "retired-gemini"
    redirect = await async_client.put(f"/api/settings/model-redirects/{source}", json={"targetModel": GEMINI})
    assert redirect.status_code == 200, redirect.text
    await _enable_api_key_auth(async_client)
    result = await async_client.post(
        "/api/api-keys/",
        json={"name": "redirected key", "allowedModels": [source], "enforcedModel": source},
    )
    assert result.status_code == 200, result.text
    response = await async_client.post(
        "/backend-api/codex/responses",
        json={"model": "ignored-by-key", "input": "Hi", "stream": False},
        headers={"Authorization": f"Bearer {result.json()['key']}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["model"] == GEMINI
    assert captured[0][0] in pool
    rows = (await async_client.get("/api/request-logs", params={"model": source})).json()["requests"]
    assert [(row["model"], row["requestedModel"]) for row in rows] == [(GEMINI, source)]


async def test_quota_exhaustion_fails_over_to_the_next_account(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch, rejections=1)

    body = await ask(async_client, GEMINI)

    assert body["status"] == "completed"
    assert [source_id for source_id, _, _ in captured] in ([pool[0], pool[1]], [pool[1], pool[0]])
    # The conversation keeps one cascade across accounts; only the project and token change.
    assert captured[0][1]["request"]["labels"]["cascade_id"] == captured[1][1]["request"]["labels"]["cascade_id"]


async def test_ban_ends_the_request_without_walking_the_pool(async_client, pool, monkeypatch):
    ban = {
        "error": {
            "code": 403,
            "status": "PERMISSION_DENIED",
            "message": "This service has been disabled in this account for violation of Terms of Service.",
        }
    }
    captured = install_upstream(monkeypatch, rejections=1, rejection=ban, rejection_status=403)

    response = await async_client.post(
        "/backend-api/codex/responses",
        json={"model": GEMINI, "input": "Hi", "stream": False, "prompt_cache_key": "conversation-ban"},
        headers={"session_id": "conversation-ban"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "antigravity_account_banned"
    assert response.headers["x-should-retry"] == "false"
    assert len(captured) == 1
    accounts = (await async_client.get("/api/antigravity-accounts")).json()["accounts"]
    holds = {account["id"]: account["hold"] for account in accounts}
    assert holds[captured[0][0]] == "banned"
    assert [hold for source_id, hold in holds.items() if source_id != captured[0][0]] == [None]


TOS_FRAME: dict[str, Any] = {
    "error": {
        "code": 403,
        "status": "PERMISSION_DENIED",
        "message": "Service disabled.",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "TOS_VIOLATION",
                "metadata": {"appeal_url": "https://forms.gle/x"},
            }
        ],
    }
}


@pytest.mark.parametrize("stream", [False, True], ids=["collected", "streamed"])
async def test_suspension_after_output_holds_the_account(async_client, pool, monkeypatch, stream):
    # Recorded where it is observed, though nothing is retried once output reached the client.
    captured = install_upstream(monkeypatch, rounds=[[HELLO[0], TOS_FRAME]])

    response = await async_client.post(
        "/backend-api/codex/responses",
        json={"model": GEMINI, "input": "Hi", "stream": stream, "prompt_cache_key": "conversation-tos"},
        headers={"session_id": "conversation-tos"},
    )

    if stream:
        assert response.status_code == 200
        assert "antigravity_account_banned" in response.text
    else:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "antigravity_account_banned"
    assert len(captured) == 1
    accounts = (await async_client.get("/api/antigravity-accounts")).json()["accounts"]
    holds = {account["id"]: account["hold"] for account in accounts}
    assert holds[captured[0][0]] == "banned"
    assert [hold for source_id, hold in holds.items() if source_id != captured[0][0]] == [None]


EMPTY: list[dict[str, Any]] = [
    {
        "response": {
            "candidates": [
                {"content": {"role": "model", "parts": [{"text": "hmm", "thought": True}]}, "finishReason": "STOP"}
            ],
            "usageMetadata": {"promptTokenCount": 12, "thoughtsTokenCount": 5},
            "responseId": "fixture",
        }
    }
]


async def _latest_log(model: str):
    from sqlalchemy import select

    from app.db.models import RequestLog

    async with SessionLocal() as session:
        row = (
            await session.scalars(select(RequestLog).where(RequestLog.model == model).order_by(RequestLog.id.desc()))
        ).first()
    assert row is not None
    return row


async def test_empty_completion_retry_reports_the_final_attempt_and_bills_both(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch, rounds=[EMPTY, HELLO])

    body = await ask(async_client, GEMINI)

    assert len(captured) == 2
    assert body["output"][-1]["content"][0]["text"] == "Hello there"
    # The client reads input tokens as its context size: only the attempt it continues from counts.
    assert (body["usage"]["input_tokens"], body["usage"]["output_tokens"]) == (12, 3)
    row = await _latest_log(GEMINI)
    assert (row.input_tokens, row.output_tokens, row.reasoning_tokens) == (24, 8, 5)


async def test_repeated_empty_completion_bills_both_attempts(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch, rounds=[EMPTY, EMPTY])

    response = await async_client.post(
        "/backend-api/codex/responses",
        json={"model": GEMINI, "input": "Hi", "stream": True, "prompt_cache_key": "conversation-empty"},
        headers={"session_id": "conversation-empty"},
    )

    assert len(captured) == 2
    assert "empty_completion" in response.text
    row = await _latest_log(GEMINI)
    assert (row.input_tokens, row.output_tokens, row.reasoning_tokens) == (24, 10, 10)


@pytest.mark.parametrize(
    ("path", "body", "headers"),
    [
        ("/backend-api/codex/responses", {"input": "Hi", "stream": False}, {}),
        (
            "/v1/messages",
            {"max_tokens": 50, "messages": [{"role": "user", "content": "Hi"}]},
            {"anthropic-version": "2023-06-01"},
        ),
    ],
    ids=["codex", "messages"],
)
@pytest.mark.parametrize(("retry_after", "sends"), [(None, 1), ("0", 2)], ids=["bare", "retry-after"])
async def test_refused_content_is_reported_final(
    async_client, pool, monkeypatch, path, body, headers, retry_after, sends
):
    from app.modules.antigravity import recovery

    monkeypatch.setattr(recovery, "_jitter", lambda: 0.0)
    bare = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Resource has been exhausted"}}
    captured = install_upstream(monkeypatch, rejections=2, rejection=bare, rejection_retry_after=retry_after)

    response = await async_client.post(path, json={"model": GEMINI, **body}, headers=headers)

    assert response.status_code == 429, response.text
    assert response.headers["x-should-retry"] == "false"
    assert "retry-after" not in response.headers
    # Only Google's Retry-After earns one same-account retry; never the pool.
    assert [source_id for source_id, _, _ in captured] == [captured[0][0]] * sends


def _capacity(*details: dict[str, Any]) -> dict[str, Any]:
    info = {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "MODEL_CAPACITY_EXHAUSTED"}
    return {"error": {"code": 503, "status": "UNAVAILABLE", "message": "No capacity", "details": [info, *details]}}


@pytest.mark.parametrize(
    ("rejection", "retry_after"),
    [
        (_capacity({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17s"}), None),
        (_capacity(), "17"),
    ],
    ids=["retry-info", "retry-after"],
)
async def test_capacity_delay_cools_the_model_and_moves(async_client, pool, monkeypatch, rejection, retry_after):
    from app.modules.antigravity import recovery

    monkeypatch.setattr(recovery, "_jitter", lambda: 0.0)
    captured = install_upstream(
        monkeypatch, rejections=1, rejection=rejection, rejection_status=503, rejection_retry_after=retry_after
    )

    await ask(async_client, GEMINI, "conversation-capacity")

    first, second = (source_id for source_id, _, _ in captured)
    assert first != second
    accounts = (await async_client.get("/api/antigravity-accounts")).json()["accounts"]
    ((cooldown,),) = [account["cooldowns"] for account in accounts if account["id"] == first]
    assert cooldown["scope"].startswith("model:")
    assert cooldown["reason"] == "capacity_exhausted"
    remaining = datetime.fromisoformat(cooldown["until"].replace("Z", "+00:00")) - datetime.now(UTC)
    assert timedelta(seconds=10) < remaining <= timedelta(seconds=17)


async def test_explicit_zero_capacity_delay_retries_in_place(async_client, pool, monkeypatch):
    from app.modules.antigravity import recovery

    monkeypatch.setattr(recovery, "_jitter", lambda: 0.0)
    captured = install_upstream(
        monkeypatch, rejections=1, rejection=_capacity(), rejection_status=503, rejection_retry_after="0"
    )

    await ask(async_client, GEMINI, "conversation-capacity-zero")

    assert [source_id for source_id, _, _ in captured] == [captured[0][0]] * 2
    accounts = (await async_client.get("/api/antigravity-accounts")).json()["accounts"]
    assert all(account["cooldowns"] == [] for account in accounts)


@pytest.mark.parametrize(("retry_after", "wait"), [(None, None), ("30", timedelta(seconds=30))], ids=["bare", "hinted"])
async def test_rate_limited_metadata_is_paced_by_google(async_client, pool, monkeypatch, retry_after, wait):
    from app.modules.antigravity.errors import MetadataHTTPError
    from app.modules.antigravity.service import INTERVALS

    limited = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Too many requests"}}
    monkeypatch.setattr(
        CloudCodeClient,
        "quota_summary",
        AsyncMock(side_effect=MetadataHTTPError("retrieveUserQuota", 429, retry_after, body=limited)),
    )

    before = datetime.now(UTC)
    response = await async_client.post(f"/api/antigravity-accounts/{pool[0]}/refresh")

    assert response.status_code == 200, response.text
    quota = response.json()["state"]["metadata"]["quota"]
    assert quota["rate_limited"] is True
    retry_at = datetime.fromisoformat(quota["retry_at"].replace("Z", "+00:00"))
    expected = before + (wait or INTERVALS["quota"])
    assert expected <= retry_at <= expected + timedelta(seconds=5)


@pytest.mark.parametrize(
    ("path", "body", "headers"),
    [
        ("/v1/responses", {"input": "Hi"}, {}),
        ("/v1/chat/completions", {"messages": [{"role": "user", "content": "Hi"}]}, {}),
        (
            "/v1/messages",
            {"max_tokens": 50, "messages": [{"role": "user", "content": "Hi"}]},
            {"anthropic-version": "2023-06-01"},
        ),
    ],
    ids=["responses", "chat", "messages"],
)
async def test_every_front_end_reaches_the_native_agent(async_client, pool, monkeypatch, path, body, headers):
    captured = install_upstream(monkeypatch)

    response = await async_client.post(path, json={"model": GEMINI, **body}, headers=headers)

    assert response.status_code == 200, response.text
    assert "Hello there" in response.text
    ((_, envelope, sent_headers),) = captured
    assert (envelope["requestType"], sent_headers["User-Agent"]) == ("agent", USER_AGENT)


async def test_chat_tool_continuation_replays_the_unsigned_call_with_the_sentinel(async_client, pool, monkeypatch):
    captured = install_upstream(monkeypatch)
    call = {"id": "call_1", "type": "function", "function": {"name": "shell", "arguments": '{"command": "ls"}'}}
    tool = {
        "type": "function",
        "function": {
            "name": "shell",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
        },
    }

    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": GEMINI,
            "tools": [tool],
            "messages": [
                {"role": "user", "content": "list files"},
                {"role": "assistant", "content": None, "tool_calls": [call]},
                {"role": "tool", "tool_call_id": "call_1", "content": "a.txt"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    contents = captured[0][1]["request"]["contents"]
    call_part = next(part for content in contents for part in content["parts"] if "functionCall" in part)
    assert call_part["functionCall"]["args"] == {"command": "ls"}
    assert call_part["thoughtSignature"] == SKIP_SIGNATURE
    assert any("functionResponse" in part for content in contents for part in content["parts"])


@pytest.mark.parametrize("stream", [False, True], ids=["json", "sse"])
async def test_web_search_runs_as_the_native_search_web_and_continues_the_response(
    async_client, pool, monkeypatch, stream
):
    search_round = [
        {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "functionCall": {"id": "fc-1", "name": "search_web", "args": {"query": "codex"}},
                                    "thoughtSignature": "sig-1",
                                }
                            ],
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2},
                "responseId": "fixture",
            }
        }
    ]
    captured = install_upstream(monkeypatch, rounds=[search_round, HELLO])
    searches: list[tuple[str, dict[str, Any], str]] = []

    async def call(self, method: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        searches.append((method, body, self.identity.user_agent))
        candidate = {
            "content": {"role": "model", "parts": [{"text": "Codex is a coding agent."}]},
            "groundingMetadata": {
                "groundingChunks": [{"web": {"uri": "https://redirect/1", "title": "openai.com"}}],
                "groundingSupports": [{"segment": {"endIndex": 24}, "groundingChunkIndices": [0]}],
            },
        }
        return {"response": {"candidates": [candidate]}}

    monkeypatch.setattr(CloudCodeClient, "call", call)

    response = await async_client.post(
        "/backend-api/codex/responses",
        json={
            "model": GEMINI,
            "input": "What is Codex?",
            "tools": [{"type": "web_search", "external_web_access": True}],
            "stream": stream,
            "prompt_cache_key": "conversation-search",
        },
        headers={"session_id": "conversation-search"},
    )

    assert response.status_code == 200, response.text
    if stream:
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: {")]
        kinds = [event["type"] for event in events]
        assert kinds.count("response.created") == 1
        assert kinds.index("response.web_search_call.searching") < kinds.index("response.web_search_call.completed")
        assert kinds[-1] == "response.completed"
        body = events[-1]["response"]
    else:
        body = response.json()
    assert body["status"] == "completed"
    assert [item["type"] for item in body["output"]] == ["reasoning", "web_search_call", "reasoning", "message"]
    assert body["output"][1]["status"] == "completed"
    assert body["output"][1]["action"] == {"type": "search", "query": "codex"}
    assert body["output"][-1]["content"][0]["text"] == "Hello there"
    ((method, search_body, user_agent),) = searches
    assert (method, search_body["requestType"], search_body["model"]) == (
        "generateContent",
        "web_search",
        "gemini-3.8-flash-lite",
    )
    assert user_agent == USER_AGENT
    # Both rounds go to the account that ran the search.
    assert len({source_id for source_id, _, _ in captured}) == 1
    first, second = (envelope["request"] for _, envelope, _ in captured)
    assert first["tools"][0]["functionDeclarations"][0]["name"] == "search_web"
    calls = [part for content in second["contents"] for part in content["parts"] if "functionCall" in part]
    assert calls == [
        {"functionCall": {"id": "fc-1", "name": "search_web", "args": {"query": "codex"}}, "thoughtSignature": "sig-1"}
    ]
    [result] = [part for content in second["contents"] for part in content["parts"] if "functionResponse" in part]
    assert "Codex is a coding agent.[1]" in result["functionResponse"]["response"]["output"]
    assert "[1] [openai.com](https://redirect/1)" in result["functionResponse"]["response"]["output"]


@pytest.mark.parametrize(
    "control",
    [{"seed": 7}, {"presence_penalty": 1}, {"logprobs": True}, {"store": True}, {"unknown_control": "kept"}],
)
async def test_chat_rejects_controls_antigravity_cannot_honour(async_client, pool, monkeypatch, control):
    captured = install_upstream(monkeypatch)

    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": GEMINI, "messages": [{"role": "user", "content": "Hi"}], **control},
    )

    assert response.status_code == 400
    assert response.json()["error"]["param"] == next(iter(control))
    assert captured == []


async def test_reconnect_and_duplicate_import_are_bound_to_the_google_subject(async_client, pool):
    duplicate = await async_client.post(
        "/api/antigravity-accounts/import", json={"name": "again", "credentials": credential_file("alpha-again")}
    )
    assert duplicate.status_code == 400
    assert "already enrolled" in duplicate.json()["error"]["message"]

    mismatch = await async_client.post(
        f"/api/antigravity-accounts/{pool[0]}/reconnect", json={"credentials": credential_file("beta")}
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["error"]["code"] == "antigravity_identity_mismatch"

    same = await async_client.post(
        f"/api/antigravity-accounts/{pool[0]}/reconnect", json={"credentials": credential_file("alpha-again")}
    )
    assert same.status_code == 200, same.text


async def test_imported_account_exposes_its_catalog_families(async_client, pool):
    response = await async_client.get("/api/antigravity-accounts")
    assert response.status_code == 200
    accounts = response.json()["accounts"]
    assert {account["id"] for account in accounts} == set(pool)
    models = await async_client.get("/backend-api/codex/models?client_version=0.163.0")
    slugs = {model["slug"] for model in models.json()["models"]}
    assert {GEMINI, CLAUDE} <= slugs
