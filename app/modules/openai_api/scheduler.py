from __future__ import annotations

import asyncio
import contextlib
import logging

from sqlalchemy import select

from app.core.scheduling.leader_election import get_leader_election
from app.core.utils.time import utcnow
from app.db.models import ModelSource, OpenAIApiAccount
from app.db.session import get_background_session
from app.modules.openai_api.repository import OpenAIApiRepository
from app.modules.openai_api.schemas import AccountState
from app.modules.openai_api.service import OpenAIApiService

logger = logging.getLogger(__name__)

CATALOG_REFRESH_SECONDS = 6 * 3600


class OpenAIApiRefreshScheduler:
    """Six-hourly catalog synchronization; OpenAI publishes no balance to poll in between."""

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
            rows = list(
                await session.scalars(
                    select(OpenAIApiAccount).join(ModelSource).where(ModelSource.is_enabled.is_(True))
                )
            )
            due = [
                row.source_id
                for row in rows
                if (updated := AccountState.model_validate_json(row.state_json).catalog_updated_at) is None
                or (utcnow() - updated).total_seconds() >= CATALOG_REFRESH_SECONDS
            ]
        for source_id in due:
            try:
                async with get_background_session() as session:
                    await OpenAIApiService(OpenAIApiRepository(session)).refresh(source_id, operator=False)
            except Exception:
                logger.exception("openai_api_refresh_failed source_id=%s", source_id)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(300)
            try:
                await get_leader_election().run_if_leader(self.refresh_once)
            except Exception:
                logger.exception("openai_api_refresh_cycle_failed")
