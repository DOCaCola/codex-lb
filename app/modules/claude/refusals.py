"""Refused translated output provenance: hashed response identities, never contents.

A client commits items it received as done before Claude's stop reason arrives. When that
reason is a refusal, Anthropic requires the refused output to be discarded rather than
continued, so later requests omit every item the refused response produced.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re

from sqlalchemy import select, update

from app.core.types import JsonValue
from app.core.utils.request_id import get_request_id
from app.core.utils.time import utcnow
from app.db.models import ClaudeResourceOrigin
from app.db.session import get_background_session
from app.modules.claude.resources import RESOURCE_TTL, record_keys

logger = logging.getLogger(__name__)
# Translated output items are identified as {response_id}_{content index}.
_ITEM_ID = re.compile(r"(resp_.+)_\d+")


def _key(client_scope: str, response_id: str) -> str:
    return hashlib.sha256(json.dumps([client_scope, "refused_response", response_id]).encode()).hexdigest()


def _response_id(item: JsonValue) -> str | None:
    identifier = item.get("id") if isinstance(item, dict) else None
    match = _ITEM_ID.fullmatch(identifier) if isinstance(identifier, str) else None
    return match.group(1) if match else None


async def record_refused_response(client_scope: str, response_id: str, source_id: str) -> None:
    """Persist before the terminal event reaches a client that retries immediately."""
    await record_keys((_key(client_scope, response_id),), source_id)


async def omit_refused_output(payload: dict[str, JsonValue], client_scope: str) -> dict[str, JsonValue]:
    items = payload.get("input")
    if not isinstance(items, list):
        return payload
    keys = {_key(client_scope, response_id): response_id for item in items if (response_id := _response_id(item))}
    if not keys:
        return payload
    async with get_background_session() as session:
        now = utcnow()
        refused_keys = list(
            await session.scalars(
                select(ClaudeResourceOrigin.resource_hash).where(
                    ClaudeResourceOrigin.resource_hash.in_(keys), ClaudeResourceOrigin.expires_at > now
                )
            )
        )
        if not refused_keys:
            return payload
        # Refused output stays in the client's history, so its record lives as long as it is used.
        await session.execute(
            update(ClaudeResourceOrigin)
            .where(ClaudeResourceOrigin.resource_hash.in_(refused_keys))
            .values(expires_at=now + RESOURCE_TTL)
        )
        await session.commit()
    refused = {keys[key] for key in refused_keys}
    kept = [item for item in items if _response_id(item) not in refused]
    logger.info(
        "claude_refused_output_omitted request_id=%s responses=%d items=%d",
        get_request_id(),
        len(refused),
        len(items) - len(kept),
    )
    return {**payload, "input": kept}
