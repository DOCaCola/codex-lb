"""Native Messages ownership. Stores a scope hash and account, never history."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from pydantic import JsonValue
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import utcnow
from app.db.models import ClaudeSessionOwner
from app.modules.claude.credentials import ClaudeError

NATIVE_SESSION_TTL = timedelta(hours=1)


def contains_account_bound_state(body: dict[str, JsonValue]) -> bool:
    messages = body.get("messages", [])
    if not isinstance(messages, list):
        raise ClaudeError("Claude messages must be an array")
    for message in messages:
        if not isinstance(message, dict):
            raise ClaudeError("Invalid Claude message")
        blocks = message.get("content")
        if isinstance(blocks, list) and any(
            isinstance(block, dict)
            and (
                block.get("type")
                in {
                    "thinking",
                    "redacted_thinking",
                    "server_tool_use",
                }
                or str(block.get("type", "")).endswith("_tool_result")
                and block.get("type") != "tool_result"
            )
            for block in blocks
        ):
            return True
    return False


class NativeSessionOwnership:
    def __init__(self, session: AsyncSession, *, client_scope: str, conversation_id: str, model: str) -> None:
        self.session = session
        self.key = hashlib.sha256(json.dumps([client_scope, conversation_id, model]).encode()).hexdigest()

    async def owner(self, *, required: bool) -> str | None:
        row = await self.session.get(ClaudeSessionOwner, self.key, populate_existing=True)
        if row is not None and row.expires_at > utcnow():
            return row.source_id
        if required:
            raise ClaudeError("Native Claude history has no retained account owner; start with portable context")
        return None

    async def claim(self, source_id: str) -> str:
        now = utcnow()
        if self.session.get_bind().dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await self.session.execute(delete(ClaudeSessionOwner).where(ClaudeSessionOwner.expires_at <= now))
        await self.session.execute(
            insert(ClaudeSessionOwner)
            .values(
                scope_hash=self.key,
                source_id=source_id,
                expires_at=now + NATIVE_SESSION_TTL,
            )
            .on_conflict_do_nothing()
        )
        # Refresh retention without changing a concurrently claimed owner.
        await self.session.execute(
            update(ClaudeSessionOwner)
            .where(ClaudeSessionOwner.scope_hash == self.key)
            .values(
                expires_at=now + NATIVE_SESSION_TTL,
            )
        )
        await self.session.commit()
        row = await self.session.get(ClaudeSessionOwner, self.key, populate_existing=True)
        assert row is not None
        return row.source_id
