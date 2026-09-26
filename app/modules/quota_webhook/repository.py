from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import TokenEncryptor
from app.db.models import (
    Account,
    QuotaWebhookBaseline,
    QuotaWebhookConfig,
    QuotaWebhookDelivery,
    QuotaWebhookRedemption,
)
from app.modules.quota_webhook.schemas import Observation, WebhookUpdate, detect_reset

logger = logging.getLogger(__name__)
MAX_PENDING = 1000


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def lock_config(session: AsyncSession, *, create: bool = False) -> QuotaWebhookConfig | None:
    if create:
        insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
        await session.execute(
            insert(QuotaWebhookConfig)
            .values(
                id=1,
                enabled=False,
                kinds='["scheduled","unexpected"]',
                generation=1,
                changed_at=now_utc(),
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
    # This write obtains the SQLite cross-process write lock as well as a
    # PostgreSQL row lock. Every baseline/config/claim mutation uses this order.
    await session.execute(
        update(QuotaWebhookConfig)
        .where(QuotaWebhookConfig.id == 1)
        .values(
            generation=QuotaWebhookConfig.generation,
        )
    )
    return await session.get(QuotaWebhookConfig, 1, populate_existing=True)


async def configure(session: AsyncSession, payload: WebhookUpdate) -> None:
    config = await lock_config(session, create=True)
    assert config is not None
    encryptor = TokenEncryptor()
    if payload.url is not None:
        config.url_encrypted = encryptor.encrypt(payload.url.get_secret_value())
    if payload.clear_url:
        config.url_encrypted = None
    if payload.signing_secret is not None:
        config.secret_encrypted = encryptor.encrypt(payload.signing_secret.get_secret_value())
    if payload.clear_signing_secret:
        config.secret_encrypted = None
    if payload.enabled and config.url_encrypted is None:
        raise ValueError("Configure a webhook URL before enabling delivery")
    config.enabled = payload.enabled
    config.kinds = json.dumps(list(dict.fromkeys(payload.kinds)))
    config.generation += 1
    config.changed_at = now_utc()
    await session.execute(delete(QuotaWebhookBaseline))
    await session.execute(
        update(QuotaWebhookDelivery)
        .where(
            QuotaWebhookDelivery.status.in_(["pending", "sending"]),
        )
        .values(status="cancelled", lease_id=None, lease_until=None)
    )
    await session.commit()


async def enqueue(
    session: AsyncSession, config: QuotaWebhookConfig, payload: dict[str, JsonValue], *, now: datetime
) -> str | None:
    pending = await session.scalar(
        select(func.count())
        .select_from(QuotaWebhookDelivery)
        .where(
            QuotaWebhookDelivery.status.in_(["pending", "sending"]),
        )
    )
    assert pending is not None
    if pending >= MAX_PENDING:
        logger.warning("quota_webhook_queue_full")
        return None
    event_id = str(uuid4())
    payload.update(schema_version=1, event_id=event_id, detected_at=now.replace(tzinfo=UTC).isoformat())
    session.add(
        QuotaWebhookDelivery(
            id=event_id,
            generation=config.generation,
            payload=json.dumps(payload, separators=(",", ":")),
            status="pending",
            attempts=0,
            created_at=now,
            next_at=now,
        )
    )
    await session.flush()
    return event_id


async def observe(
    session: AsyncSession,
    account_id: str,
    windows: list[tuple[str, Observation]],
    *,
    observed_at: datetime,
) -> bool:
    config = await lock_config(session)
    if config is None or not config.enabled:
        return False
    account = await session.get(Account, account_id)
    if account is None:
        return True
    identity = json.dumps([account.chatgpt_account_id, account.chatgpt_user_id, account.email, account.plan_type])
    redemption = (
        await session.get(QuotaWebhookRedemption, account.chatgpt_account_id) if account.chatgpt_account_id else None
    )
    now = now_utc()
    # An omitted window is unknown, not zero. Reappearance starts a new
    # baseline rather than interpreting a degraded snapshot as a reset.
    present = [window for window, _ in windows]
    await session.execute(
        update(QuotaWebhookBaseline)
        .where(
            QuotaWebhookBaseline.account_id == account_id,
            QuotaWebhookBaseline.window.not_in(present),
            QuotaWebhookBaseline.observed_at < observed_at,
        )
        .values(snapshot="null", observed_at=observed_at)
    )
    for window, sample in windows:
        observed_at = sample.observed_at.astimezone(UTC).replace(tzinfo=None)
        if observed_at <= config.changed_at:
            continue
        baseline = await session.get(QuotaWebhookBaseline, (account_id, window))
        if baseline is not None and observed_at <= baseline.observed_at:
            continue
        suppressed = redemption is not None and observed_at <= redemption.suppress_until
        if baseline is not None and baseline.snapshot != "null" and baseline.identity == identity and not suppressed:
            before = Observation.model_validate_json(baseline.snapshot)
            kind = detect_reset(before, sample)
            if kind is not None and kind in json.loads(config.kinds):
                await enqueue(
                    session,
                    config,
                    {
                        "type": "quota.reset",
                        "kind": kind,
                        "provider": "openai",
                        "account_id": account_id,
                        "window": window,
                        "window_minutes": sample.window_minutes,
                        "used_percent_before": before.used_percent,
                        "used_percent_after": sample.used_percent,
                        "previous_reset_at": _deadline(before.reset_at),
                        "reset_at": _deadline(sample.reset_at),
                        "observed_at": sample.observed_at.isoformat(),
                    },
                    now=now,
                )
        if baseline is None:
            baseline = QuotaWebhookBaseline(account_id=account_id, window=window)
            session.add(baseline)
        baseline.identity = identity
        baseline.snapshot = sample.model_dump_json()
        baseline.observed_at = observed_at
    return True


def _deadline(value: int | None) -> str | None:
    return datetime.fromtimestamp(value, UTC).isoformat() if value and value > 0 else None


async def redemption_intent(session: AsyncSession, upstream_account_id: str) -> None:
    config = await lock_config(session)
    if config is not None and config.enabled:
        row = await session.get(QuotaWebhookRedemption, upstream_account_id)
        if row is None:
            row = QuotaWebhookRedemption(upstream_account_id=upstream_account_id)
            session.add(row)
        row.suppress_until = now_utc() + timedelta(minutes=10)
        # Do not compare a post-redemption sample against pre-redemption usage,
        # even if no refresh happens until after the suppression interval.
        await session.execute(
            delete(QuotaWebhookBaseline).where(
                QuotaWebhookBaseline.account_id.in_(
                    select(Account.id).where(Account.chatgpt_account_id == upstream_account_id)
                ),
            )
        )
    await session.commit()


@dataclass(frozen=True)
class ClaimedDelivery:
    event_id: str
    lease_id: str
    generation: int
    url: str = field(repr=False)
    secret: str | None = field(repr=False)
    payload: str = field(repr=False)


async def claim(session: AsyncSession) -> ClaimedDelivery | None:
    config = await lock_config(session)
    now = now_utc()
    await session.execute(delete(QuotaWebhookDelivery).where(QuotaWebhookDelivery.created_at < now - timedelta(days=7)))
    await session.execute(delete(QuotaWebhookRedemption).where(QuotaWebhookRedemption.suppress_until < now))
    if config is None or not config.enabled:
        await session.commit()
        return None
    await session.execute(
        update(QuotaWebhookDelivery)
        .where(
            QuotaWebhookDelivery.status.in_(["pending", "sending"]),
            or_(
                QuotaWebhookDelivery.created_at < now - timedelta(minutes=15),
                (QuotaWebhookDelivery.attempts >= 4) & (QuotaWebhookDelivery.lease_until < now),
            ),
        )
        .values(status="failed", last_error="delivery_budget_exhausted", lease_id=None, lease_until=None)
    )
    row = await session.scalar(
        select(QuotaWebhookDelivery)
        .where(
            QuotaWebhookDelivery.generation == config.generation,
            QuotaWebhookDelivery.attempts < 4,
            or_(
                (QuotaWebhookDelivery.status == "pending") & (QuotaWebhookDelivery.next_at <= now),
                (QuotaWebhookDelivery.status == "sending") & (QuotaWebhookDelivery.lease_until < now),
            ),
        )
        .order_by(QuotaWebhookDelivery.created_at)
        .limit(1)
    )
    if row is None:
        await session.commit()
        return None
    row.status, row.lease_id, row.lease_until = "sending", str(uuid4()), now + timedelta(seconds=45)
    row.attempts += 1
    encryptor = TokenEncryptor()
    assert config.url_encrypted is not None
    assert row.lease_id is not None
    result = ClaimedDelivery(
        row.id,
        row.lease_id,
        config.generation,
        encryptor.decrypt(config.url_encrypted),
        encryptor.decrypt(config.secret_encrypted) if config.secret_encrypted else None,
        row.payload,
    )
    await session.commit()
    return result


async def settle(
    session: AsyncSession,
    delivery: ClaimedDelivery,
    *,
    status: int | None,
    error: str | None,
    retryable: bool,
    retry_after: int = 0,
) -> None:
    config = await lock_config(session)
    row = await session.get(QuotaWebhookDelivery, delivery.event_id, populate_existing=True)
    if row is None or row.lease_id != delivery.lease_id or config is None or config.generation != delivery.generation:
        await session.commit()
        return
    now = now_utc()
    row.last_http_status, row.last_error = status, error
    row.lease_id, row.lease_until = None, None
    if error is None:
        row.status = "delivered"
    elif retryable and row.attempts < 4 and now < row.created_at + timedelta(minutes=15):
        row.status = "pending"
        row.next_at = now + timedelta(seconds=max(5 * 2 ** (row.attempts - 1), min(retry_after, 300)))
    else:
        row.status = "failed"
    await session.commit()
