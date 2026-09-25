from __future__ import annotations

import asyncio
import contextlib
import logging

from sqlalchemy import select

from app.core.scheduling.leader_election import get_leader_election
from app.core.utils.time import utcnow
from app.db.models import ModelSource, OpenRouterAccount
from app.db.session import get_background_session
from app.modules.openrouter.repository import OpenRouterRepository
from app.modules.openrouter.schemas import AccountState
from app.modules.openrouter.service import OpenRouterService

logger = logging.getLogger(__name__)


class OpenRouterRefreshScheduler:
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
                    select(OpenRouterAccount.source_id).join(ModelSource).where(ModelSource.is_enabled.is_(True))
                )
            )
        for source_id in ids:
            try:
                async with get_background_session() as session:
                    row = await session.get(OpenRouterAccount, source_id)
                    if row is None:
                        continue
                    state = AccountState.model_validate_json(row.state_json)
                    refresh_catalog = (
                        state.catalog_updated_at is None
                        or (utcnow() - state.catalog_updated_at).total_seconds() >= 6 * 3600
                    )
                    await OpenRouterService(OpenRouterRepository(session)).refresh(source_id, catalog=refresh_catalog)
            except Exception:
                logger.exception("openrouter_refresh_failed source_id=%s", source_id)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                await get_leader_election().run_if_leader(self.refresh_once)
            except Exception:
                logger.exception("openrouter_refresh_cycle_failed")
