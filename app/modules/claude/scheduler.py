from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.scheduling.leader_election import get_leader_election
from app.db.models import ClaudeAccount, ModelSource
from app.db.session import get_background_session
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState
from app.modules.claude.service import ClaudeService
from app.modules.claude.version import ClaudeVersionService

logger = logging.getLogger(__name__)


class ClaudeRefreshScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def refresh_once(self) -> None:
        async with get_background_session() as session:
            ids = list(
                await session.scalars(
                    select(ClaudeAccount.source_id)
                    .join(ModelSource)
                    .where(ModelSource.is_enabled.is_(True), ClaudeAccount.credential_status == "ready")
                )
            )
        # No unsolicited discovery traffic in installations without Claude.
        if not ids:
            return
        async with get_background_session() as session:
            await ClaudeVersionService(session).refresh()
        for source_id in ids:
            try:
                async with get_background_session() as session:
                    row = await session.get(ClaudeAccount, source_id)
                    if row is None:
                        continue
                    state = AccountState.model_validate_json(row.state_json)
                    catalog_due = state.catalog_updated_at is None or datetime.now(
                        UTC
                    ) - state.catalog_updated_at >= timedelta(hours=6)
                    await ClaudeService(ClaudeRepository(session)).refresh(source_id, catalog=catalog_due)
            except Exception:
                # Never emit exception bodies from credential-bearing operations.
                logger.warning("claude_metadata_refresh_failed source_id=%s", source_id)

    async def _run(self) -> None:
        while True:
            try:
                await get_leader_election().run_if_leader(self.refresh_once)
            except Exception:
                logger.warning("claude_metadata_cycle_failed")
            await asyncio.sleep(60)


def build_claude_refresh_scheduler() -> ClaudeRefreshScheduler:
    return ClaudeRefreshScheduler()
