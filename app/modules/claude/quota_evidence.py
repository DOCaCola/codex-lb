"""Serialize quota mutations with reset settlement; keep causal evidence scoped."""

from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeAccount, ClaudeCooldown
from app.modules.claude.schemas import AccountState
from app.modules.model_sources.service import ModelSourceNotFoundError


class Restriction(BaseModel):
    window: str
    until: datetime
    requested_at: datetime


class Evidence(BaseModel):
    restrictions: list[Restriction] = Field(default_factory=list)


async def lock_account(session: AsyncSession, source_id: str) -> ClaudeAccount:
    changed = await session.scalar(
        update(ClaudeAccount)
        .where(ClaudeAccount.source_id == source_id)
        .values(version=ClaudeAccount.version + 1)
        .returning(ClaudeAccount.source_id)
        .execution_options(synchronize_session=False)
    )
    if changed is None:
        raise ModelSourceNotFoundError("Claude account not found")
    row = await session.get(ClaudeAccount, source_id, populate_existing=True)
    assert row is not None
    return row


def read_evidence(row: ClaudeCooldown) -> Evidence:
    if row.evidence_json is not None:
        return Evidence.model_validate_json(row.evidence_json)
    # Existing rows have no causal provenance. Never infer a resettable window.
    return Evidence(
        restrictions=[
            Restriction(
                window="unknown",
                until=row.until.replace(tzinfo=UTC),
                requested_at=datetime.min.replace(tzinfo=UTC),
            )
        ]
    )


async def save_evidence(session: AsyncSession, row: ClaudeCooldown, evidence: Evidence, now: datetime) -> None:
    active = [item for item in evidence.restrictions if item.until > now]
    # Remove dominated observations without losing an older, longer deadline.
    evidence.restrictions = [
        item
        for index, item in enumerate(active)
        if not any(
            other.window == item.window
            and other.until >= item.until
            and other.requested_at >= item.requested_at
            and (other.until > item.until or other.requested_at > item.requested_at or other_index > index)
            for other_index, other in enumerate(active)
            if other_index != index
        )
    ]
    if not evidence.restrictions:
        await session.delete(row)
        return
    row.until = max(item.until for item in evidence.restrictions).replace(tzinfo=None)
    row.evidence_json = evidence.model_dump_json()


async def reconcile_reset(
    session: AsyncSession,
    account: ClaudeAccount,
    cleared: Sequence[str],
    barrier: datetime,
) -> None:
    state = AccountState.model_validate_json(account.state_json)
    for window in cleared:
        state.reset_barriers[window] = max(state.reset_barriers.get(window, barrier), barrier)
    account.state_json = state.model_dump_json()
    rows = list(await session.scalars(select(ClaudeCooldown).where(ClaudeCooldown.source_id == account.source_id)))
    for row in rows:
        evidence = read_evidence(row)
        evidence.restrictions = [
            item for item in evidence.restrictions if item.window not in cleared or item.requested_at > barrier
        ]
        await save_evidence(session, row, evidence, datetime.now(UTC))
