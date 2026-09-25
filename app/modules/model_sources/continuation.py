"""Private Responses retention for stateless provider accounts."""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import cast

from starlette.requests import Request

from app.core.config.settings import get_settings
from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.sse import parse_sse_data_json
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy._service.support import _request_log_client_fields
from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope
from app.modules.proxy.affinity import _owner_lookup_session_id_from_headers
from app.modules.proxy.replay_output import ReplayOutputCollector


class SourceContinuation:
    def __init__(
        self, request: Request, api_key: ApiKeyData | None, source_id: str, *, retain_incomplete: bool = False
    ) -> None:
        _, _, conversation_id = _request_log_client_fields(request.headers)
        self.scope = ReplayScope(
            api_key.id if api_key else None,
            conversation_id or _owner_lookup_session_id_from_headers(request.headers) or "source-responses",
        )
        self.store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
        self.source_id = source_id
        self.payload: dict[str, JsonValue] = {}
        self.retain_incomplete = retain_incomplete

    async def expand(self, payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
        result = deepcopy(payload)
        previous = result.get("previous_response_id")
        if isinstance(previous, str) and previous:
            history = await self.store.load(self.scope, previous)
            if history is None:
                raise ClientPayloadError(
                    "Previous response was not found; resend complete history without previous_response_id.",
                    param="previous_response_id",
                    code="previous_response_not_found",
                )
            delta = result.get("input", [])
            if isinstance(delta, str):
                delta = [{"role": "user", "content": delta}]
            if not isinstance(delta, list):
                raise ClientPayloadError("Input must be text or a list", param="input")
            result["input"] = history.expand(cast(list[JsonValue], delta))
            result.pop("previous_response_id", None)
        result["store"] = False
        self.payload = result
        return deepcopy(result)

    async def remember(self, response: dict[str, JsonValue], output: list[JsonValue] | None = None) -> None:
        response_id = response.get("id")
        items = output if output is not None else response.get("output")
        statuses = {"completed", "incomplete"} if self.retain_incomplete else {"completed"}
        if response.get("status") not in statuses or not isinstance(response_id, str) or not isinstance(items, list):
            return
        await self.store.remember(self.scope, response_id, json.dumps(self.payload), items, self.source_id)

    async def stream(self, body: AsyncIterator[str]) -> AsyncIterator[str]:
        output = ReplayOutputCollector()
        try:
            async for frame in body:
                event = parse_sse_data_json(frame)
                if event is not None:
                    if event.get("type") == "response.output_item.done":
                        output.retain(event)
                    elif event.get("type") == "response.completed" or (
                        self.retain_incomplete and event.get("type") == "response.incomplete"
                    ):
                        response = event.get("response")
                        if isinstance(response, dict):
                            items = output.finish(response.get("output"))
                            if items is not None:
                                # Publish before the completion reaches a client that can
                                # immediately send the next tool turn on this socket.
                                await self.remember(response, items)
                yield frame
        finally:
            if inspect.isasyncgen(body):
                await body.aclose()
