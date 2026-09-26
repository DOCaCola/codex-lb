from __future__ import annotations

import asyncio
import contextlib
import logging

from app.db.session import get_background_session
from app.modules.quota_webhook.repository import claim, settle
from app.modules.quota_webhook.transport import deliver

logger = logging.getLogger(__name__)


class QuotaWebhookWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="quota-reset-webhook")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def run_once(self) -> bool:
        async with get_background_session() as session:
            delivery = await claim(session)
        if delivery is None:
            return False
        result = await deliver(delivery)
        async with get_background_session() as session:
            await settle(
                session,
                delivery,
                status=result.status,
                error=result.error,
                retryable=result.retryable,
                retry_after=result.retry_after,
            )
        if result.error:
            logger.warning("quota_webhook_delivery_failed event_id=%s reason=%s", delivery.event_id, result.error)
        return True

    async def _run(self) -> None:
        while True:
            try:
                if await self.run_once():
                    continue
            except Exception:
                logger.warning("quota_webhook_worker_failed")
            await asyncio.sleep(5)


def build_quota_webhook_scheduler() -> QuotaWebhookWorker:
    return QuotaWebhookWorker()
