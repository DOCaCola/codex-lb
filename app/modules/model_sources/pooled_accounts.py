"""Account pools of API-key providers: rotation, routing policy and cooldowns per account and model."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import to_utc_naive, utcnow
from app.db.models import ModelSource, OpenAIApiAccount, OpenRouterAccount, SourceCooldown
from app.db.session import get_background_session

_ACCOUNT_TABLES: dict[str, type[OpenRouterAccount] | type[OpenAIApiAccount]] = {
    "openrouter": OpenRouterAccount,
    "openai_apikey": OpenAIApiAccount,
}
POOLED_KINDS = frozenset(_ACCOUNT_TABLES)
# Structured billing refusals (opencodex's set plus OpenAI's insufficient_quota): the account's
# credit is gone, so every model on it is skipped until the credit renews.
BILLING_EXHAUSTION_CODES = frozenset(
    {
        "insufficient_quota",
        "credit_balance_exhausted",
        "credit_balance_too_low",
        "insufficient_balance",
        "billing_hard_limit_reached",
        "organization_spend_limit_exceeded",
        "project_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    }
)
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
    if not sources or sources[0].kind not in POOLED_KINDS:
        return sources[0] if sources else None
    kind = sources[0].kind
    blocked = set(
        await session.scalars(
            select(SourceCooldown.source_id).where(
                SourceCooldown.source_id.in_([source.id for source in sources]),
                SourceCooldown.model.in_(("*", model)),
                SourceCooldown.until > utcnow(),
            )
        )
    )
    candidates = [source for source in sources if source.kind == kind and source.id not in blocked]
    if not candidates:
        # Preserve ownership while cooling down. Dispatch reports the actual
        # condition; returning None would incorrectly select ChatGPT instead.
        return sources[0]
    table = _ACCOUNT_TABLES[kind]
    policies = dict(
        (
            await session.execute(
                select(table.source_id, table.routing_policy).where(
                    table.source_id.in_([source.id for source in candidates])
                )
            )
        ).all()
    )
    rank = {"burn_first": 0, "normal": 1, "preserve": 2}
    priority = min(rank[policies[source.id]] for source in candidates)
    candidates = [source for source in candidates if rank[policies[source.id]] == priority]
    if not advance_rotation:
        return candidates[0]
    index = _rotation.pop(model, 0)
    _rotation[model] = index + 1
    if len(_rotation) > 4096:
        _rotation.popitem(last=False)
    return candidates[index % len(candidates)]


async def cooldown_until(session: AsyncSession, source_id: str, model: str = "*") -> datetime | None:
    return await session.scalar(
        select(SourceCooldown.until)
        .where(
            SourceCooldown.source_id == source_id,
            SourceCooldown.model.in_(("*", model)),
            SourceCooldown.until > utcnow(),
        )
        .order_by(SourceCooldown.until.desc())
        .limit(1)
    )


async def cooldown_remaining(source_id: str, model: str) -> int:
    async with get_background_session() as session:
        deadline = await cooldown_until(session, source_id, model)
    return max(1, int((deadline - utcnow()).total_seconds())) if deadline else 0


def _retry_after_seconds(retry_after: str | None) -> int:
    if retry_after:
        try:
            return max(1, int(retry_after))
        except ValueError:
            try:
                return max(1, int((to_utc_naive(parsedate_to_datetime(retry_after)) - utcnow()).total_seconds()))
            except (ValueError, TypeError, OverflowError):
                pass
    return 60


async def _billing_exhausted_until(session: AsyncSession, source_id: str) -> datetime:
    from app.modules.openai_api.credit import BILLING_EXHAUSTION_FALLBACK, credit_cycle
    from app.modules.openai_api.schemas import AccountState

    now = utcnow()
    account = await session.get(OpenAIApiAccount, source_id)
    renews_on = AccountState.model_validate_json(account.state_json).credit_renews_on if account else None
    return credit_cycle(renews_on, now)[1] if renews_on is not None else now + BILLING_EXHAUSTION_FALLBACK


async def record_failure(source_id: str, model: str, status: int, retry_after: str | None, code: str | None) -> None:
    async with get_background_session() as session:
        if code in BILLING_EXHAUSTION_CODES:
            scope, until = "*", await _billing_exhausted_until(session, source_id)
        else:
            scope = "*" if status in (401, 402) else model
            until = utcnow() + timedelta(seconds=min(_retry_after_seconds(retry_after), 86400))
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        statement = insert(SourceCooldown).values(source_id=source_id, model=scope, until=until)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[SourceCooldown.source_id, SourceCooldown.model],
                set_={"until": case((SourceCooldown.until > until, SourceCooldown.until), else_=until)},
            )
        )
        await session.commit()


async def clear_cooldowns(session: AsyncSession, source_id: str) -> None:
    """An operator refresh: the account is tried again on the next request."""
    await session.execute(delete(SourceCooldown).where(SourceCooldown.source_id == source_id))
