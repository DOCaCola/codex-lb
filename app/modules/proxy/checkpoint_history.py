"""Scoped recovery of visible input behind native compaction checkpoints.

Only successful compactions observed here establish a mapping. This does not
decode provider-private state, guess history, or shorten semantic content.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from copy import deepcopy

from app.core.config.settings import get_settings
from app.core.openai.compaction import (
    CODEX_LB_COMPACTION_PREFIX,
    lower_opaque_compaction_items_for_model_source,
    project_source_compaction_item,
)
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.models import CompactResponsePayload
from app.core.openai.requests import ResponsesCompactRequest
from app.core.types import JsonValue
from app.core.utils.request_id import get_request_id
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy._service.support import _request_log_client_fields
from app.modules.proxy.affinity import _owner_lookup_session_id_from_headers
from app.modules.proxy.checkpoint_handoff import CheckpointResolver, checkpoint_digest, remember_checkpoint_origin
from app.modules.proxy.replay_store import HTTPFallbackReplayStore, ReplayScope

logger = logging.getLogger(__name__)
_METADATA = frozenset({"id", "status", "metadata", "client_metadata", "internal_chat_message_metadata_passthrough"})
_CALLS = {
    "function_call": frozenset({"type", "call_id", "name", "namespace", "arguments"}),
    "custom_tool_call": frozenset({"type", "call_id", "name", "namespace", "input"}),
    "apply_patch_call": frozenset({"type", "call_id", "operation"}),
}
_OUTPUTS = {f"{kind}_output": kind for kind in _CALLS}


class UnreadableCheckpointHistory(ValueError):
    """A bounded reason, never input content."""


def checkpoint_scope(headers: Mapping[str, str], api_key: ApiKeyData | None) -> ReplayScope | None:
    conversation_id = _request_log_client_fields(headers)[2] or _owner_lookup_session_id_from_headers(headers)
    if api_key is None or not conversation_id:
        return None
    return ReplayScope(api_key.id, conversation_id)


def checkpoint_store() -> HTTPFallbackReplayStore:
    return HTTPFallbackReplayStore(get_settings().data_dir / "checkpoint-history")


def _readable_parts(value: JsonValue) -> JsonValue:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise UnreadableCheckpointHistory("invalid_message_content")
    result: list[JsonValue] = []
    for part in value:
        if not isinstance(part, dict):
            raise UnreadableCheckpointHistory("invalid_message_content")
        kind = part.get("type")
        if not isinstance(kind, str) or kind not in {
            "input_text",
            "output_text",
            "text",
            "refusal",
            "input_image",
            "input_file",
        }:
            raise UnreadableCheckpointHistory("unsupported_message_content")
        if any(key in part for key in ("file_id", "encrypted_content", "signature")):
            raise UnreadableCheckpointHistory("bound_message_content")
        image_url = part.get("image_url")
        if part.get("type") == "input_image" and (
            not isinstance(image_url, str) or not image_url.startswith(("data:", "https://", "http://"))
        ):
            raise UnreadableCheckpointHistory("bound_message_content")
        result.append({key: deepcopy(data) for key, data in part.items() if key not in _METADATA})
    return result


def readable_checkpoint_input(items: JsonValue) -> list[JsonValue]:
    """Retain semantic input, excluding only known nonportable/protocol state."""
    if isinstance(items, str):
        items = [{"type": "message", "role": "user", "content": items}]
    if not isinstance(items, list):
        raise UnreadableCheckpointHistory("invalid_input")
    result: list[JsonValue] = []
    calls: dict[tuple[str, str], int] = {}
    for item in items:
        if not isinstance(item, dict):
            raise UnreadableCheckpointHistory("unknown_input")
        kind = item.get("type", "message")
        if not isinstance(kind, str):
            raise UnreadableCheckpointHistory("invalid_item_type")
        if kind in {"additional_tools", "compaction_trigger"}:
            continue
        if (
            kind == "context_compaction"
            and item.get("encrypted_content") is None
            and item.keys() <= (_METADATA | {"type", "encrypted_content"})
        ):
            continue
        semantic = {key: value for key, value in item.items() if key not in _METADATA}
        if kind == "reasoning":
            if semantic.keys() - {"type", "summary", "content", "encrypted_content"}:
                raise UnreadableCheckpointHistory("unknown_reasoning")
            texts: list[str] = []
            for field, part_kind in (("summary", "summary_text"), ("content", "reasoning_text")):
                parts = item.get(field)
                if parts is None:
                    parts = []
                if not isinstance(parts, list):
                    raise UnreadableCheckpointHistory("invalid_reasoning")
                field_texts: list[str] = []
                for part in parts:
                    if (
                        not isinstance(part, dict)
                        or part.get("type") != part_kind
                        or not isinstance(part.get("text"), str)
                    ):
                        raise UnreadableCheckpointHistory("invalid_reasoning")
                    text = part["text"]
                    assert isinstance(text, str)
                    if text.strip():
                        field_texts.append(text)
                if field == "summary" or field_texts != texts:
                    texts.extend(field_texts)
            if texts:
                result.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": t} for t in texts],
                    }
                )
            continue
        if kind == "message":
            role = semantic.get("role")
            if (
                semantic.keys() - {"type", "role", "content", "phase"}
                or not isinstance(role, str)
                or role
                not in {
                    "user",
                    "assistant",
                    "developer",
                    "system",
                }
            ):
                raise UnreadableCheckpointHistory("unknown_message")
            semantic["type"] = "message"
            semantic["content"] = _readable_parts(item.get("content"))
        elif kind in _CALLS:
            if semantic.keys() - _CALLS[kind]:
                raise UnreadableCheckpointHistory("unknown_tool_call")
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                raise UnreadableCheckpointHistory("invalid_tool_call")
            key = (kind, call_id)
            calls[key] = calls.get(key, 0) + 1
        elif kind in _OUTPUTS:
            if semantic.keys() - {"type", "call_id", "output"}:
                raise UnreadableCheckpointHistory("unknown_tool_output")
            call_id = item.get("call_id")
            key = (_OUTPUTS[kind], call_id) if isinstance(call_id, str) else None
            if key is None or calls.get(key, 0) != 1:
                raise UnreadableCheckpointHistory("unpaired_tool_output")
            calls.pop(key)
        else:
            raise UnreadableCheckpointHistory("unsupported_state")
        result.append(deepcopy(semantic))
    return result


class CheckpointHistory:
    def __init__(self, store: HTTPFallbackReplayStore, scope: ReplayScope | None) -> None:
        self.store = store
        self.scope = scope

    async def materialize(
        self, payload: dict[str, JsonValue], resolve: CheckpointResolver | None = None
    ) -> dict[str, JsonValue]:
        items = payload.get("input")
        if self.scope is None or not isinstance(items, list):
            return payload
        result: list[JsonValue] = []
        recovered = 0
        for index, item in enumerate(items):
            ciphertext = item.get("encrypted_content") if isinstance(item, dict) else None
            if (
                not isinstance(item, dict)
                or item.get("type") not in ("compaction", "compaction_summary")
                or item.keys() - (_METADATA | {"type", "encrypted_content"})
                or not isinstance(ciphertext, str)
                or not ciphertext
                or ciphertext.startswith(CODEX_LB_COMPACTION_PREFIX)
            ):
                if isinstance(item, dict) and item.get("type") in (
                    "compaction",
                    "compaction_summary",
                    "context_compaction",
                ):
                    project_source_compaction_item(item, index)
                result.append(item)
                continue
            history = await self.store.load(self.scope, checkpoint_digest(ciphertext))
            if history is None:
                if resolve is not None:
                    handed_off = await resolve(self.scope, item)
                    if handed_off is not None:
                        result.extend(handed_off)
                        recovered += 1
                        continue
                project_source_compaction_item(item, index)
                raise AssertionError("opaque checkpoint projection must reject a cache miss")
            prefix = history.output
            if prefix and len(result) >= len(prefix):
                try:
                    candidate = readable_checkpoint_input(result[-len(prefix) :])
                except UnreadableCheckpointHistory:
                    candidate = None
                if candidate == prefix:
                    del result[-len(prefix) :]
            result.extend(history.input)
            recovered += 1
        if not recovered:
            return payload
        logger.info("compaction_checkpoint_materialized request_id=%s count=%d", get_request_id(), recovered)
        return {**payload, "input": result}

    async def remember(
        self, request: ResponsesCompactRequest, response: CompactResponsePayload, account_id: str
    ) -> None:
        if self.scope is None or response.error is not None or response.status not in (None, "completed"):
            return
        output = (response.model_extra or {}).get("output")
        if not isinstance(output, list):
            return
        checkpoints = [
            (index, item)
            for index, item in enumerate(output)
            if isinstance(item, dict) and item.get("type") in ("compaction", "compaction_summary")
        ]
        if len(checkpoints) != 1:
            return
        index, checkpoint = checkpoints[0]
        ciphertext = checkpoint.get("encrypted_content")
        if (
            index != len(output) - 1
            or not isinstance(ciphertext, str)
            or not ciphertext
            or ciphertext.startswith(CODEX_LB_COMPACTION_PREFIX)
            or checkpoint.get("status") not in (None, "completed")
        ):
            return
        try:
            payload = request.model_dump(mode="json", exclude_none=True)
            if any(payload.get(handle) is not None for handle in ("previous_response_id", "conversation", "prompt")):
                raise UnreadableCheckpointHistory("unresolved_handle")
            payload = await self.materialize(payload)
            lower_opaque_compaction_items_for_model_source(payload)
            retained = readable_checkpoint_input(payload["input"])
            if not retained:
                raise UnreadableCheckpointHistory("empty_readable_history")
            prefix = readable_checkpoint_input(output[:index])
            if request.instructions.strip():
                instructions: JsonValue = {"type": "message", "role": "developer", "content": request.instructions}
                if not retained or retained[0] != instructions:
                    retained.insert(0, instructions)
        except UnreadableCheckpointHistory as exc:
            logger.info("compaction_checkpoint_not_retained reason=%s", exc)
            return
        except ClientPayloadError:
            logger.info("compaction_checkpoint_not_retained reason=unresolved_checkpoint")
            return
        await self.store.remember(
            self.scope,
            checkpoint_digest(ciphertext),
            json.dumps({"model": request.model, "input": retained}),
            prefix,
            account_id,
        )


async def materialize_source_checkpoints(
    payload: dict[str, JsonValue],
    headers: Mapping[str, str],
    api_key: ApiKeyData | None,
    *,
    resolve: CheckpointResolver | None = None,
) -> dict[str, JsonValue]:
    return await CheckpointHistory(checkpoint_store(), checkpoint_scope(headers, api_key)).materialize(payload, resolve)


async def retain_checkpoint_provenance(
    model: str, response: CompactResponsePayload, scope: ReplayScope | None, account_id: str
) -> None:
    if scope is None or response.error is not None or response.status not in (None, "completed"):
        return
    output = (response.model_extra or {}).get("output")
    if not isinstance(output, list):
        return
    checkpoints = [item for item in output if isinstance(item, dict) and is_checkpoint_item(item)]
    if len(checkpoints) != 1 or checkpoints[0] is not output[-1]:
        return
    item = checkpoints[0]
    ciphertext = item.get("encrypted_content")
    if not isinstance(ciphertext, str) or not ciphertext or ciphertext.startswith(CODEX_LB_COMPACTION_PREFIX):
        return
    if item.get("status") not in (None, "completed"):
        return
    await remember_checkpoint_origin(scope, model, account_id, item)


async def retain_native_checkpoint(
    request: ResponsesCompactRequest,
    response: CompactResponsePayload,
    headers: Mapping[str, str],
    api_key: ApiKeyData | None,
    account_id: str,
) -> None:
    await retain_checkpoint_provenance(request.model, response, checkpoint_scope(headers, api_key), account_id)


def is_checkpoint_item(item: JsonValue) -> bool:
    return isinstance(item, dict) and item.get("type") in ("compaction", "compaction_summary")


async def retain_streamed_checkpoint(
    request_text: str,
    response: dict[str, JsonValue],
    scope: ReplayScope,
    account_id: str,
) -> None:
    # The caller owns validated response.create JSON and has completed settlement.
    request = json.loads(request_text)
    await retain_completed_checkpoint(request["model"], response, scope, account_id)


async def retain_completed_checkpoint(
    model: str,
    response: dict[str, JsonValue],
    scope: ReplayScope,
    account_id: str,
) -> None:
    # Successful native completion establishes provenance even for native deltas;
    # ``response`` carries the output reconstructed from ``output_item.done``.
    # No readable input or provider ciphertext is retained.
    result = CompactResponsePayload.model_validate({**response, "object": "response.compaction"})
    await retain_checkpoint_provenance(model, result, scope, account_id)
