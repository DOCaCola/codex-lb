from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.antigravity import search as search_module
from app.modules.antigravity.catalog import search_model
from app.modules.antigravity.constants import SKIP_SIGNATURE
from app.modules.antigravity.errors import AntigravityError, MetadataHTTPError
from app.modules.antigravity.opaque import AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.protocol import SEARCH_IDENTITY, project_responses
from app.modules.antigravity.responses import GeminiProjection
from app.modules.antigravity.schemas import CatalogFamily
from app.modules.antigravity.search import (
    SearchCall,
    SearchContext,
    SearchOutcome,
    SearchPolicy,
    failure,
    run_search,
    search_envelope,
    search_policy,
    summary,
)
from app.modules.antigravity.tool_names import GoogleToolNames
from app.modules.antigravity.version import ClientIdentity
from app.modules.claude.tool_names import ToolIdentity

OPAQUE = AntigravityOpaqueState(TokenEncryptor(key=Fernet.generate_key()))
GEMINI = CatalogFamily(
    id="gemini-3.8-flash",
    display_name="Gemini 3.8 Flash",
    tiers={"low": "gemini-3.8-flash-low", "high": "gemini-3.8-flash-high"},
    api_provider="API_PROVIDER_GOOGLE_GEMINI",
    quota_family="gemini",
    max_output_tokens=65_536,
    supports_thinking=True,
)
SCOPE = ThoughtScope("src-1", "project-1", GEMINI.id, GEMINI.anthropic_wire, "client-1")
SEARCH = {"type": "web_search"}
SHELL = {
    "type": "function",
    "name": "shell",
    "description": "Run a command",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
}
CREATED = datetime(2026, 10, 30, 9, 0, 0, tzinfo=UTC)
COMPLETED = datetime(2026, 10, 30, 9, 0, 2, tzinfo=UTC)
CONTEXT = SearchContext(
    model="gemini-3.8-flash-lite",
    project_id="project-1",
    access_token="token",
    identity=ClientIdentity("1.4.10", "123", "darwin_arm64"),
    policy=SearchPolicy(),
    source_id="src-1",
)


def _project(payload: dict[str, Any], **options: Any):
    return project_responses(payload, family=GEMINI, max_output_tokens=65_536, scope=SCOPE, opaque=OPAQUE, **options)


def _grounded(text: str, chunks: list[dict[str, Any]], supports: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = {
        "content": {"role": "model", "parts": [{"text": text}]},
        "groundingMetadata": {"groundingChunks": chunks, "groundingSupports": supports},
    }
    return {"response": {"candidates": [candidate]}}


# Catalog


def test_search_model_follows_the_cli_rule() -> None:
    tiered = {"tieredModelIds": {"flashLite": ["flash-lite-1"]}}
    assert search_model(tiered) == "flash-lite-1"
    assert search_model({**tiered, "webSearchModelIds": ["search-1"]}) == "search-1"
    # Without the Flash Lite tier the CLI fails every search, even with webSearchModelIds.
    assert search_model({"webSearchModelIds": ["search-1"]}) is None
    assert search_model({}) is None


# The client's tool


def test_search_policy_accepts_codex_options() -> None:
    assert search_policy({"type": "web_search"}, param="tools[0]") == SearchPolicy()
    policy = search_policy(
        {"type": "web_search", "external_web_access": True, "filters": {"allowed_domains": ["a.org"]}, "max_uses": 2},
        param="tools[0]",
    )
    assert policy == SearchPolicy(("a.org",), 2)
    assert search_policy({"type": "web_search", "external_web_access": False}, param="tools[0]") is None


@pytest.mark.parametrize(
    "tool",
    [
        {"type": "web_search", "search_context_size": "high"},
        {"type": "web_search", "filters": {"allowed_domains": []}},
        {"type": "web_search", "filters": {"blocked_domains": ["a.org"]}},
        {"type": "web_search", "max_uses": 0},
        {"type": "web_search", "external_web_access": "yes"},
    ],
)
def test_search_policy_rejects_what_it_cannot_honour(tool: dict[str, Any]) -> None:
    with pytest.raises(ClientPayloadError) as raised:
        search_policy(tool, param="tools[3]")
    assert raised.value.param == "tools[3]"


# The search request and its result


def test_search_envelope_matches_the_cli_capture() -> None:
    call = SearchCall("item-1", "call-1", {"query": "codex release", "domain": "github.com"})
    body = search_envelope(CONTEXT, call)
    assert list(body) == ["project", "request", "model", "userAgent", "requestType"]
    assert (body["model"], body["userAgent"], body["requestType"]) == (
        "gemini-3.8-flash-lite",
        "antigravity",
        "web_search",
    )
    request = body["request"]
    assert request["contents"] == [{"role": "user", "parts": [{"text": "codex release"}]}]
    assert request["tools"] == [
        {"googleSearch": {"enhancedContent": {"imageSearch": {"maxResultCount": 5}}, "includedDomains": ["github.com"]}}
    ]
    assert request["generationConfig"] == {"candidateCount": 1}


def test_client_domain_filter_bounds_the_model_domain() -> None:
    restricted = SearchContext(**{**CONTEXT.__dict__, "policy": SearchPolicy(("a.org", "b.org"))})
    inside = search_envelope(restricted, SearchCall("i", "c", {"query": "q", "domain": "b.org"}))
    outside = search_envelope(restricted, SearchCall("i", "c", {"query": "q", "domain": "evil.org"}))
    assert inside["request"]["tools"][0]["googleSearch"]["includedDomains"] == ["b.org"]
    assert outside["request"]["tools"][0]["googleSearch"]["includedDomains"] == ["a.org", "b.org"]
    unbounded = search_envelope(CONTEXT, SearchCall("i", "c", {"query": "q"}))
    assert "includedDomains" not in unbounded["request"]["tools"][0]["googleSearch"]


def test_summary_inserts_citations_at_utf8_offsets() -> None:
    text = "Grüße aus Berlin. Zweiter Satz."
    first = len("Grüße aus Berlin.".encode())
    data = _grounded(
        text,
        [{"web": {"uri": "https://r/1", "title": "one.de"}}, {"web": {"uri": "https://r/2", "domain": "two.de"}}],
        [
            {"segment": {"endIndex": first}, "groundingChunkIndices": [0]},
            {"segment": {"endIndex": len(text.encode())}, "groundingChunkIndices": [0, 1]},
        ],
    )
    assert summary("grüße", data, CREATED, COMPLETED) == "\n".join(
        [
            "Created At: 2026-10-30T09:00:00Z",
            "Completed At: 2026-10-30T09:00:02Z",
            'The search for "grüße" returned the following summary:',
            "Grüße aus Berlin.[1] Zweiter Satz.[1][2]",
            "",
            "Sources:",
            "[1] [one.de](https://r/1)",
            "[2] [two.de](https://r/2)",
            "",
            "Note: Source URLs are HTTP redirects; check where they resolve if you need the direct link.",
        ]
    )


def test_summary_without_sources_omits_the_sources_block() -> None:
    result = summary("q", _grounded("Nothing found.", [], []), CREATED, COMPLETED)
    assert "Sources:" not in result
    assert result.endswith(
        "Nothing found.\n\nNote: Source URLs are HTTP redirects; check where they resolve if you need the direct link."
    )


@pytest.mark.parametrize(
    "data",
    [
        {"response": {"candidates": []}},
        _grounded("x", [{"web": {}}], []),
        _grounded("x", [], [{"segment": {"endIndex": 99}, "groundingChunkIndices": []}]),
        _grounded("x", [], [{"segment": {"endIndex": 1}, "groundingChunkIndices": [0]}]),
    ],
)
def test_invalid_search_responses_are_rejected(data: dict[str, Any]) -> None:
    with pytest.raises(AntigravityError):
        summary("q", data, CREATED, COMPLETED)


def test_failure_is_worded_as_the_cli_tool_error() -> None:
    assert failure(CREATED, COMPLETED, "boom") == {
        "error": "Created At: 2026-10-30T09:00:00Z\nCompleted At: 2026-10-30T09:00:02Z\n"
        "Encountered error in tool execution: boom"
    }


@pytest.mark.asyncio
async def test_run_search_answers_with_the_grounded_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[str, dict[str, Any]]] = []

    async def call(self: Any, method: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        sent.append((method, body))
        return _grounded("Found it.", [], [])

    monkeypatch.setattr(search_module.CloudCodeClient, "call", call)
    outcome = await run_search(CONTEXT, SearchCall("item-1", "call-1", {"query": "q"}), allowed=True)
    assert outcome.succeeded
    assert "Found it." in outcome.response["output"]
    assert [method for method, _ in sent] == ["generateContent"]


@pytest.mark.asyncio
async def test_run_search_failures_become_the_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def call(self: Any, method: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        raise MetadataHTTPError("generateContent", 429)

    monkeypatch.setattr(search_module.CloudCodeClient, "call", call)
    outcome = await run_search(CONTEXT, SearchCall("item-1", "call-1", {"query": "q"}), allowed=True)
    assert not outcome.succeeded
    assert "Encountered error in tool execution:" in outcome.response["error"]


@pytest.mark.asyncio
async def test_search_beyond_the_limit_is_not_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    async def call(self: Any, method: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("no request beyond the limit")

    monkeypatch.setattr(search_module.CloudCodeClient, "call", call)
    outcome = await run_search(CONTEXT, SearchCall("item-1", "call-1", {"query": "q"}), allowed=False)
    assert not outcome.succeeded
    assert "limit of 8 searches" in outcome.response["error"]


# Request projection


def test_search_is_declared_first_under_the_cli_name() -> None:
    projection = _project({"input": "x", "tools": [SHELL, SEARCH]}, searchable=True)
    declarations = projection.request["tools"][0]["functionDeclarations"]
    assert [declaration["name"] for declaration in declarations] == ["search_web", "shell"]
    assert declarations[0]["parameters"]["required"] == ["query"]
    assert projection.search == SearchPolicy()
    assert projection.tools.resolve("search_web") == SEARCH_IDENTITY


def test_search_is_not_offered_without_a_search_model_or_live_access() -> None:
    for payload, searchable in (
        ({"input": "x", "tools": [SHELL, SEARCH]}, False),
        ({"input": "x", "tools": [SHELL, {**SEARCH, "external_web_access": False}]}, True),
    ):
        projection = _project(payload, searchable=searchable)
        declarations = projection.request["tools"][0]["functionDeclarations"]
        assert [declaration["name"] for declaration in declarations] == ["shell"]
        assert projection.search is None


def test_forced_web_search_maps_to_the_search_function() -> None:
    forced = _project({"input": "x", "tools": [SEARCH], "tool_choice": {"type": "web_search"}}, searchable=True)
    assert forced.request["toolConfig"] == {
        "functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["search_web"]}
    }
    with pytest.raises(ClientPayloadError) as raised:
        _project({"input": "x", "tools": [SEARCH], "tool_choice": {"type": "web_search"}})
    assert raised.value.param == "tool_choice"


def test_duplicate_search_tools_are_rejected() -> None:
    with pytest.raises(ClientPayloadError):
        _project({"input": "x", "tools": [SEARCH, SEARCH]}, searchable=True)


def _sealed_searches(*searches: tuple[str, str, dict[str, Any]]) -> dict[str, Any]:
    sealed = [
        SearchOutcome(SearchCall(item_id, call_id, {"query": "q"}), response, True).sealed()
        for item_id, call_id, response in searches
    ]
    return {
        "type": "reasoning",
        "summary": [],
        "encrypted_content": OPAQUE.seal(SCOPE, text="", signature=None, searches=sealed),
    }


def test_replayed_search_round_becomes_call_result_and_next_round() -> None:
    projection = _project(
        {
            "tools": [SEARCH],
            "input": [
                {"role": "user", "content": "news?"},
                {
                    "type": "reasoning",
                    "summary": [],
                    "encrypted_content": OPAQUE.seal(SCOPE, text="plan", signature="sig-1"),
                },
                {
                    "id": "ws-1",
                    "type": "web_search_call",
                    "status": "completed",
                    "action": {"type": "search", "query": "q"},
                },
                _sealed_searches(("ws-1", "fc-1", {"output": "summary"})),
                {"role": "assistant", "content": [{"type": "output_text", "text": "Here is the news."}]},
                {"role": "user", "content": "thanks"},
            ],
        },
        searchable=True,
    )
    contents = projection.request["contents"]
    assert [content["role"] for content in contents] == ["user", "model", "model", "model", "user"]
    assert contents[1]["parts"] == [
        {"text": "plan", "thought": True},
        {"functionCall": {"id": "fc-1", "name": "search_web", "args": {"query": "q"}}, "thoughtSignature": "sig-1"},
    ]
    assert contents[2]["parts"] == [
        {"functionResponse": {"id": "fc-1", "name": "search_web", "response": {"output": "summary"}}}
    ]
    assert contents[3]["parts"] == [{"text": "Here is the news."}]


def test_search_results_join_the_client_results_of_a_mixed_step() -> None:
    projection = _project(
        {
            "tools": [SEARCH, SHELL],
            "input": [
                {"role": "user", "content": "go"},
                {
                    "id": "ws-1",
                    "type": "web_search_call",
                    "status": "completed",
                    "action": {"type": "search", "query": "q"},
                },
                {
                    "type": "function_call",
                    "call_id": "call-1",
                    "name": "shell",
                    "arguments": json.dumps({"command": "ls"}),
                },
                _sealed_searches(("ws-1", "fc-1", {"output": "summary"})),
                {"type": "function_call_output", "call_id": "call-1", "output": "a.txt"},
            ],
        },
        searchable=True,
    )
    contents = projection.request["contents"]
    assert [content["role"] for content in contents] == ["user", "model", "model"]
    search_call, shell_call = contents[1]["parts"]
    assert search_call["functionCall"]["name"] == "search_web"
    assert search_call["thoughtSignature"] == SKIP_SIGNATURE
    assert shell_call["functionCall"]["name"] == "shell"
    assert [next(iter(part["functionResponse"].values())) for part in contents[2]["parts"]] == ["fc-1", "call-1"]


def test_search_history_without_search_offered_is_context_only() -> None:
    projection = _project(
        {
            "input": [
                {"role": "user", "content": "news?"},
                {
                    "id": "ws-1",
                    "type": "web_search_call",
                    "status": "completed",
                    "action": {"type": "search", "query": "q"},
                },
                _sealed_searches(("ws-1", "fc-1", {"output": "summary"})),
                {"role": "assistant", "content": [{"type": "output_text", "text": "Here is the news."}]},
                {"role": "user", "content": "thanks"},
            ],
        },
    )
    contents = projection.request["contents"]
    assert [content["role"] for content in contents] == ["user", "model", "user"]
    assert contents[1]["parts"] == [{"text": "Here is the news."}]


# Stream projection


def _stream() -> GeminiProjection:
    tools = GoogleToolNames()
    tools.add(SEARCH_IDENTITY)
    tools.add(ToolIdentity("shell", None, False))
    return GeminiProjection("antigravity/gemini-3.8-flash", SCOPE, tools, OPAQUE, True)


def _line(*parts: dict[str, Any], finish: str | None = None, usage: dict[str, int] | None = None) -> dict[str, Any]:
    candidate: dict[str, Any] = {"content": {"role": "model", "parts": list(parts)}}
    if finish:
        candidate["finishReason"] = finish
    response: dict[str, Any] = {"candidates": [candidate], "responseId": "abc"}
    if usage:
        response["usageMetadata"] = usage
    return {"response": response}


def _run(projection: GeminiProjection, *lines: dict[str, Any]) -> list[dict[str, Any]]:
    return [event for line in lines for event in projection.consume(line)]  # type: ignore[arg-type]


def _search_call(call_id: str = "fc-1", query: str = "news") -> dict[str, Any]:
    return {"functionCall": {"id": call_id, "name": "search_web", "args": {"query": query}}}


def test_search_round_continues_the_same_response() -> None:
    projection = _stream()
    first = _run(
        projection,
        _line({"text": "Let me look.", "thoughtSignature": "sig-1"}),
        _line(_search_call(), finish="STOP", usage={"promptTokenCount": 100, "candidatesTokenCount": 5}),
    )
    kinds = [event["type"] for event in first]
    assert "response.completed" not in kinds
    assert kinds[-3:] == [
        "response.output_item.added",
        "response.web_search_call.in_progress",
        "response.web_search_call.searching",
    ]
    assert projection.awaiting_search
    [call] = projection.pending_searches()
    assert (call.call_id, call.query) == ("fc-1", "news")

    closed = projection.complete_searches([SearchOutcome(call, {"output": "summary"}, True)])
    assert [event["type"] for event in closed] == [
        "response.web_search_call.completed",
        "response.output_item.done",
        "response.output_item.added",
        "response.output_item.done",
    ]
    assert not projection.stopped
    sealed = OPAQUE.open(closed[-1]["item"]["encrypted_content"], client_scope="client-1", param="input")
    assert [(search.item_id, search.response) for search in sealed.searches] == [(call.item_id, {"output": "summary"})]

    second = _run(
        projection,
        _line({"text": "Here it is."}, finish="STOP", usage={"promptTokenCount": 150, "candidatesTokenCount": 4}),
    )
    assert "response.created" not in [event["type"] for event in second]
    response = second[-1]["response"]
    assert second[-1]["type"] == "response.completed"
    output = response["output"]
    assert [item["type"] for item in output] == ["message", "reasoning", "web_search_call", "reasoning", "message"]
    assert output[0]["phase"] == "commentary"
    assert output[2]["status"] == "completed"
    assert output[2]["action"] == {"type": "search", "query": "news"}
    assert output[4]["phase"] == "final_answer"
    assert (response["usage"]["input_tokens"], response["usage"]["output_tokens"]) == (250, 9)


def test_mixed_round_completes_for_the_client_calls() -> None:
    projection = _stream()
    _run(
        projection,
        _line(_search_call(), {"functionCall": {"id": "fc-2", "name": "shell", "args": {"command": "ls"}}}),
        _line(finish="STOP"),
    )
    [call] = projection.pending_searches()
    events = projection.complete_searches([SearchOutcome(call, failure(CREATED, COMPLETED, "boom"), False)])
    assert "response.web_search_call.completed" not in [event["type"] for event in events]
    assert events[-1]["type"] == "response.completed"
    output = events[-1]["response"]["output"]
    assert [item["type"] for item in output] == ["web_search_call", "function_call", "reasoning"]
    assert output[0]["status"] == "failed"


def test_searches_of_an_unfinished_round_never_ran() -> None:
    projection = _stream()
    events = _run(projection, _line(_search_call(), finish="MAX_TOKENS"))
    assert not projection.awaiting_search
    assert events[-1]["type"] == "response.incomplete"
    [search] = [item for item in events[-1]["response"]["output"] if item["type"] == "web_search_call"]
    assert search["status"] == "failed"


def test_search_call_without_a_query_is_invalid() -> None:
    with pytest.raises(AntigravityError):
        _run(_stream(), _line({"functionCall": {"id": "fc-1", "name": "search_web", "args": {"query": " "}}}))
