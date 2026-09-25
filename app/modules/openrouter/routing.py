from __future__ import annotations

from collections import OrderedDict
from datetime import timedelta
from email.utils import parsedate_to_datetime

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import to_utc_naive, utcnow
from app.db.models import ModelSource, OpenRouterCooldown
from app.db.session import get_background_session

_rotation: OrderedDict[str, int] = OrderedDict()


async def select_available(
    session: AsyncSession,
    sources: list[ModelSource],
    model: str,
    *,
    excluded: set[str] | None = None,
    advance_rotation: bool = True,
) -> ModelSource | None:
    sources = [source for source in sources if source.id not in (excluded or set())]
    if not sources or sources[0].kind != "openrouter":
        return sources[0] if sources else None
    blocked = set(
        await session.scalars(
            select(OpenRouterCooldown.source_id).where(
                OpenRouterCooldown.source_id.in_([source.id for source in sources]),
                OpenRouterCooldown.model.in_(("*", model)),
                OpenRouterCooldown.until > utcnow(),
            )
        )
    )
    candidates = [source for source in sources if source.kind == "openrouter" and source.id not in blocked]
    if not candidates:
        # Preserve ownership while cooling down. Dispatch reports the actual
        # condition; returning None would incorrectly select ChatGPT instead.
        return sources[0]
    if not advance_rotation:
        return candidates[0]
    index = _rotation.pop(model, 0)
    _rotation[model] = index + 1
    if len(_rotation) > 4096:
        _rotation.popitem(last=False)
    return candidates[index % len(candidates)]


async def cooldown_remaining(source_id: str, model: str) -> int:
    async with get_background_session() as session:
        deadlines = list(
            await session.scalars(
                select(OpenRouterCooldown.until).where(
                    OpenRouterCooldown.source_id == source_id,
                    OpenRouterCooldown.model.in_(("*", model)),
                    OpenRouterCooldown.until > utcnow(),
                )
            )
        )
    return max(1, int((max(deadlines) - utcnow()).total_seconds())) if deadlines else 0


async def record_failure(source_id: str, model: str, status: int, retry_after: str | None) -> None:
    seconds = 60
    if retry_after:
        try:
            seconds = max(1, int(retry_after))
        except ValueError:
            try:
                seconds = max(1, int((to_utc_naive(parsedate_to_datetime(retry_after)) - utcnow()).total_seconds()))
            except (ValueError, TypeError, OverflowError):
                pass
    scope = "*" if status in (401, 402) else model
    async with get_background_session() as session:
        until = utcnow() + timedelta(seconds=min(seconds, 86400))
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        statement = insert(OpenRouterCooldown).values(source_id=source_id, model=scope, until=until)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[OpenRouterCooldown.source_id, OpenRouterCooldown.model],
                set_={"until": case((OpenRouterCooldown.until > until, OpenRouterCooldown.until), else_=until)},
            )
        )
        await session.commit()
