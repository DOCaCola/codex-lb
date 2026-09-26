import json
from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QuotaWebhookConfig, QuotaWebhookDelivery
from app.modules.quota_webhook.repository import configure, enqueue, lock_config, now_utc
from app.modules.quota_webhook.schemas import DeliveryStatus, QueuedTest, WebhookStatus, WebhookUpdate
from app.modules.quota_webhook.transport import validate_url


class QuotaWebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def status(self) -> WebhookStatus:
        config = await self.session.get(QuotaWebhookConfig, 1)
        result = WebhookStatus()
        if config:
            result.enabled = config.enabled
            result.kinds = WebhookUpdate.model_validate(
                {"enabled": config.enabled, "kinds": json.loads(config.kinds)}
            ).kinds
            result.url_configured = config.url_encrypted is not None
            result.signing_secret_configured = config.secret_encrypted is not None
        result.pending = (
            await self.session.scalar(
                select(func.count())
                .select_from(QuotaWebhookDelivery)
                .where(
                    QuotaWebhookDelivery.status.in_(["pending", "sending"]),
                )
            )
            or 0
        )
        last = await self.session.scalar(
            select(QuotaWebhookDelivery)
            .order_by(
                QuotaWebhookDelivery.created_at.desc(),
                QuotaWebhookDelivery.id.desc(),
            )
            .limit(1)
        )
        if last:
            result.last_delivery = DeliveryStatus(
                event_id=last.id,
                status=last.status,
                attempts=last.attempts,
                created_at=last.created_at.replace(tzinfo=UTC),
                http_status=last.last_http_status,
                error=last.last_error,
            )
        return result

    async def update(self, payload: WebhookUpdate) -> WebhookStatus:
        if (payload.url is not None and payload.clear_url) or (
            payload.signing_secret is not None and payload.clear_signing_secret
        ):
            raise ValueError("Do not replace and clear the same secret")
        if payload.url is not None:
            validate_url(payload.url.get_secret_value())
        if payload.signing_secret is not None and not 16 <= len(payload.signing_secret.get_secret_value()) <= 4096:
            raise ValueError("Signing secret must contain 16 to 4096 characters")
        await configure(self.session, payload)
        return await self.status()

    async def test(self) -> QueuedTest:
        config = await lock_config(self.session)
        if config is None or not config.enabled or config.url_encrypted is None:
            raise ValueError("Enable and save the webhook before testing")
        event_id = await enqueue(self.session, config, {"type": "quota.test"}, now=now_utc())
        if event_id is None:
            raise ValueError("Webhook delivery queue is full")
        await self.session.commit()
        return QueuedTest(event_id=event_id)
