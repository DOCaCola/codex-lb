"""Claude session affinity. Stores a scope hash and account, never history."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import utcnow
from app.db.models import ClaudeAccount, ClaudeSessionOwner
from app.db.session import get_background_session
from app.modules.claude.resources import ResourceScope, touch_origins
from app.modules.model_sources.forwarding import ModelSourceForwardingError

NATIVE_SESSION_TTL = timedelta(hours=1)


async def record_admission(source_id: str) -> None:
    async with get_background_session() as session:
        await session.execute(
            update(ClaudeAccount).where(ClaudeAccount.source_id == source_id).values(last_selected_at=utcnow())
        )
        await session.commit()


@dataclass(frozen=True)
class NativeSessionBinding:
    client_scope: str
    conversation_id: str
    model: str
    retained_owner: str | None
    resource_keys: tuple[str, ...] = ()

    @property
    def resource_scope(self) -> ResourceScope:
        return ResourceScope(self.client_scope, self.model)

    async def commit(self, source_id: str) -> None:
        """Persist affinity only after admission, without overwriting a concurrent binding."""
        if self.resource_keys:
            await touch_origins(self.resource_keys, source_id)
            return
        async with get_background_session() as session:
            ownership = NativeSessionOwnership(
                session, client_scope=self.client_scope, conversation_id=self.conversation_id, model=self.model
            )
            current = await ownership.owner()
            if current == self.retained_owner:
                claimed = await ownership.claim(source_id, replace_source_id=self.retained_owner)
                if claimed == source_id:
                    return
            elif current == source_id:
                return
        raise ModelSourceForwardingError(
            status_code=503,
            payload={
                "error": {
                    "type": "server_error",
                    "code": "claude_session_changed",
                    "message": "Claude session ownership changed during admission; retry the request.",
                }
            },
            retry_after="1",
        )


class NativeSessionOwnership:
    def __init__(self, session: AsyncSession, *, client_scope: str, conversation_id: str, model: str) -> None:
        self.session = session
        self.key = hashlib.sha256(json.dumps([client_scope, conversation_id, model]).encode()).hexdigest()

    async def owner(self) -> str | None:
        row = await self.session.get(ClaudeSessionOwner, self.key, populate_existing=True)
        if row is not None and row.expires_at > utcnow():
            return row.source_id
        return None

    async def claim(self, source_id: str, *, replace_source_id: str | None = None) -> str:
        now = utcnow()
        if self.session.get_bind().dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await self.session.execute(delete(ClaudeSessionOwner).where(ClaudeSessionOwner.expires_at <= now))
        if replace_source_id is not None and replace_source_id != source_id:
            await self.session.execute(
                update(ClaudeSessionOwner)
                .where(ClaudeSessionOwner.scope_hash == self.key, ClaudeSessionOwner.source_id == replace_source_id)
                .values(source_id=source_id)
                .returning(ClaudeSessionOwner.source_id)
            )
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
