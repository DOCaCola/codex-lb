"""Scoped native server-tool provenance; never store conversation contents."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

from pydantic import JsonValue
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import utcnow
from app.db.models import ClaudeAccount, ClaudeResourceOrigin
from app.db.session import get_background_session
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.quota_evidence import lock_account
from app.modules.claude.schemas import AccountState
from app.modules.model_sources.forwarding import ModelSourceForwardingError

RESOURCE_TTL = timedelta(days=30)


class ResourceOriginMissing(ClaudeError):
    """The caller's retained provider state has expired or was never recorded."""


def resource_ids(value: JsonValue) -> frozenset[str]:
    """Visit protocol objects only, never opaque user tool arguments/results."""
    found: set[str] = set()

    def visit(node: JsonValue) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            kind = node.get("type")
            if kind == "tool_result":
                content = node.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") in ("image", "document"):
                            visit(block)
                return
            if kind in ("tool_use", "text", "thinking", "redacted_thinking"):
                return
            if node.get("container") is not None or node.get("file_id") is not None:
                raise ClaudeError("Native Claude file/container provenance is not supported")
            is_result = isinstance(kind, str) and kind.endswith("_tool_result")
            if kind == "server_tool_use" or is_result:
                identifier = node.get("tool_use_id" if is_result else "id")
                if not isinstance(identifier, str) or not identifier:
                    raise ClaudeError("Claude server resource requires a nonempty identifier")
                found.add(identifier)
                # Result content can contain provider resource references.
                if is_result:
                    visit(node.get("content"))
                return
            for key in ("messages", "content", "content_block", "message", "source"):
                if key in node:
                    visit(node[key])

    visit(value)
    return frozenset(found)


@dataclass(frozen=True)
class ResourceScope:
    client_scope: str
    model: str

    def keys(self, identifiers: frozenset[str], *, kind: str = "server_tool") -> tuple[str, ...]:
        return tuple(
            hashlib.sha256(json.dumps([self.client_scope, self.model, kind, identifier]).encode()).hexdigest()
            for identifier in sorted(identifiers)
        )


async def resolve_origins(session: AsyncSession, keys: tuple[str, ...]) -> str | None:
    if not keys:
        return None
    rows = list(
        await session.scalars(
            select(ClaudeResourceOrigin).where(
                ClaudeResourceOrigin.resource_hash.in_(keys), ClaudeResourceOrigin.expires_at > utcnow()
            )
        )
    )
    if len(rows) != len(keys):
        raise ResourceOriginMissing("Native Claude resource origin is unknown or expired; resend portable context")
    owners = {row.source_id for row in rows}
    if len(owners) != 1:
        raise ClaudeError("Native Claude history contains conflicting resource owners")
    owner = owners.pop()
    account = await session.get(ClaudeAccount, owner, populate_existing=True)
    assert account is not None
    identity_generation = AccountState.model_validate_json(account.state_json).identity_generation
    if any(row.identity_generation != identity_generation for row in rows):
        raise ResourceOriginMissing("Native Claude resource belongs to a replaced identity; resend portable context")
    return owner


async def touch_origins(keys: tuple[str, ...], source_id: str, *, identity_generation: int = 1) -> None:
    async with get_background_session() as session:
        account = await lock_account(session, source_id)
        if AccountState.model_validate_json(account.state_json).identity_generation != identity_generation:
            raise ResourceOriginMissing("Native Claude resource identity changed during admission")
        now = utcnow()
        touched = list(
            await session.scalars(
                update(ClaudeResourceOrigin)
                .where(
                    ClaudeResourceOrigin.resource_hash.in_(keys),
                    ClaudeResourceOrigin.source_id == source_id,
                    ClaudeResourceOrigin.identity_generation == identity_generation,
                    ClaudeResourceOrigin.expires_at > now,
                )
                .values(expires_at=now + RESOURCE_TTL)
                .returning(ClaudeResourceOrigin.resource_hash)
            )
        )
        if len(touched) != len(keys):
            raise ClaudeError("Native Claude resource origin expired during admission")
        await session.commit()


async def record_origins(
    scope: ResourceScope, source_id: str, value: dict[str, JsonValue], *, identity_generation: int = 1
) -> None:
    """Commit before publishing native output; failures must never trigger replay."""
    await record_keys(scope.keys(resource_ids(value)), source_id, identity_generation=identity_generation)


async def record_keys(
    keys: tuple[str, ...], source_id: str, *, identity_generation: int = 1, require_current_identity: bool = True
) -> None:
    """Persist account ownership without storing provider identifiers or contents."""
    try:
        if not keys:
            return
        async with get_background_session() as session:
            if require_current_identity:
                account = await lock_account(session, source_id)
                if AccountState.model_validate_json(account.state_json).identity_generation != identity_generation:
                    raise ClaudeError("Claude account identity changed before resource persistence")
            now = utcnow()
            if session.get_bind().dialect.name == "postgresql":
                from sqlalchemy.dialects.postgresql import insert
            else:
                from sqlalchemy.dialects.sqlite import insert
            expired = (
                select(ClaudeResourceOrigin.resource_hash)
                .where(ClaudeResourceOrigin.expires_at <= now)
                .order_by(ClaudeResourceOrigin.expires_at)
                .limit(500)
            )
            await session.execute(
                delete(ClaudeResourceOrigin).where(
                    ClaudeResourceOrigin.resource_hash.in_(expired), ClaudeResourceOrigin.expires_at <= now
                )
            )
            for key in keys:
                written = await session.scalar(
                    insert(ClaudeResourceOrigin)
                    .values(
                        resource_hash=key,
                        source_id=source_id,
                        identity_generation=identity_generation,
                        created_at=now,
                        expires_at=now + RESOURCE_TTL,
                    )
                    .on_conflict_do_update(
                        index_elements=[ClaudeResourceOrigin.resource_hash],
                        set_={"expires_at": now + RESOURCE_TTL},
                        where=(ClaudeResourceOrigin.source_id == source_id)
                        & (ClaudeResourceOrigin.identity_generation == identity_generation),
                    )
                    .returning(ClaudeResourceOrigin.resource_hash)
                )
                if written is None:
                    raise ClaudeError("Claude resource origin conflicts with an existing account")
            await session.commit()
    except (SQLAlchemyError, ClaudeError) as exc:
        raise ModelSourceForwardingError(
            status_code=502,
            payload={
                "error": {
                    "type": "upstream_error",
                    "code": "claude_resource_provenance_failed",
                    "message": "Could not persist Claude resource provenance; response stopped",
                }
            },
        ) from exc
