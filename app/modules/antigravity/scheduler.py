from __future__ import annotations

import asyncio
import contextlib
import logging

from sqlalchemy import select

from app.core.scheduling.leader_election import get_leader_election
from app.db.models import AntigravityAccount, ModelSource
from app.db.session import get_background_session
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.service import AntigravityService
from app.modules.antigravity.version import AntigravityVersionService

logger = logging.getLogger(__name__)


class AntigravityRefreshScheduler:
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
                    select(AntigravityAccount.source_id)
                    .join(ModelSource)
                    .where(
                        ModelSource.is_enabled.is_(True),
                        AntigravityAccount.credential_status == "ready",
                        AntigravityAccount.hold.is_(None),
                    )
                )
            )
        # No manifest or Google traffic in installations without usable Antigravity accounts.
        if not ids:
            return
        async with get_background_session() as session:
            await AntigravityVersionService(session).refresh()
        for source_id in ids:
            try:
                async with get_background_session() as session:
                    await AntigravityService(AntigravityRepository(session)).refresh(source_id, force=False)
            except Exception:
                # Never emit exception bodies from credential-bearing operations.
                logger.warning("antigravity_metadata_refresh_failed source_id=%s", source_id)

    async def _run(self) -> None:
        while True:
            try:
                await get_leader_election().run_if_leader(self.refresh_once)
            except Exception:
                logger.warning("antigravity_metadata_cycle_failed")
            await asyncio.sleep(60)


def build_antigravity_refresh_scheduler() -> AntigravityRefreshScheduler:
    return AntigravityRefreshScheduler()
