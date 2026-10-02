"""Repair retained request costs while preserving permanent folded history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage.logs import RequestLogLike, calculated_cost_from_log
from app.core.usage.service_tiers import billable_service_tier
from app.db.models import (
    AccountUsageRollup,
    AccountUsageRollupState,
    ApiKeyUsageRollup,
    RequestDemandQuarterRollup,
    RequestLog,
    RequestReportHourlyRollup,
    RequestUsageHourlyRollup,
)
from app.db.session import sqlite_writer_section
from app.modules.accounts.usage_rollup import lock_fold_state
from app.modules.accounts.usage_time_rollup import (
    CONVERSATION_WHITESPACE,
    epoch_seconds,
    mirror_request_log_repricing_into_time_rollups,
    to_dimension,
)

_EXCLUDED_KINDS = ("warmup", "limit_warmup")
_UNPROVEN_TIER_ECHOES = ("default", "auto")


@dataclass(frozen=True)
class BackfillBatch:
    scanned: int
    updated: int
    last_id: int


async def backfill_missing_costs(session: AsyncSession, *, after_id: int = 0, limit: int = 200) -> BackfillBatch:
    """Commit one bounded batch; NULL is the durable idempotency marker.

    Cursor progress is merely an optimization. Restarting at zero is safe.
    Never rebuild aggregate buckets from raw: retention may have pruned part
    of a bucket, and its permanent sums must survive intact.
    """
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    async with sqlite_writer_section():
        try:
            await lock_fold_state(session)
            state = await session.get(AccountUsageRollupState, 1, populate_existing=True)
            assert state is not None
            logs = (
                await session.scalars(
                    select(RequestLog)
                    .where(
                        RequestLog.id > after_id,
                        RequestLog.cost_usd.is_(None),
                        RequestLog.model_source_id.is_(None),
                        or_(RequestLog.model_source_kind.is_(None), RequestLog.model_source_kind == "subscription"),
                        RequestLog.input_tokens.is_not(None),
                        or_(RequestLog.output_tokens.is_not(None), RequestLog.reasoning_tokens.is_not(None)),
                    )
                    .order_by(RequestLog.id)
                    .limit(limit)
                    .with_for_update()
                )
            ).all()
            updated = 0
            for log in logs:
                cost = calculated_cost_from_log(cast(RequestLogLike, log))
                if cost is None:
                    continue
                await _mirror_cost(session, state, log, cost)
                log.cost_usd = cost
                updated += 1
            await session.commit()
            return BackfillBatch(len(logs), updated, logs[-1].id if logs else after_id)
        except BaseException:
            await session.rollback()
            raise


async def repair_echoed_service_tiers(session: AsyncSession, *, after_id: int = 0, limit: int = 200) -> BackfillBatch:
    """Re-bill Fast turns whose Codex backend echo overwrote the billable tier.

    The backend echoes ``default``/``auto`` on turns it served on the
    requested tier; rows persisted before billable tiers were settled by
    :func:`billable_service_tier` carry that echo as their billable tier and
    a standard-rate cost. The settled tier is the idempotency marker: a
    repaired row leaves the selection. Folded aggregates receive the exact
    difference, never a rebuild from raw.
    """
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    async with sqlite_writer_section():
        try:
            await lock_fold_state(session)
            state = await session.get(AccountUsageRollupState, 1, populate_existing=True)
            assert state is not None
            logs = (
                await session.scalars(
                    select(RequestLog)
                    .where(
                        RequestLog.id > after_id,
                        RequestLog.model_source_id.is_(None),
                        or_(RequestLog.model_source_kind.is_(None), RequestLog.model_source_kind == "subscription"),
                        RequestLog.requested_service_tier == "priority",
                        RequestLog.actual_service_tier.in_(_UNPROVEN_TIER_ECHOES),
                        RequestLog.service_tier.in_(_UNPROVEN_TIER_ECHOES),
                    )
                    .order_by(RequestLog.id)
                    .limit(limit)
                    .with_for_update()
                )
            ).all()

            async def reprice() -> None:
                for log in logs:
                    log.service_tier = billable_service_tier(log.requested_service_tier, log.actual_service_tier)
                    if log.cost_usd is None:
                        continue
                    cost = calculated_cost_from_log(cast(RequestLogLike, log))
                    if cost is None:
                        continue
                    delta = cost - log.cost_usd
                    await _mirror_lifetime_cost(session, state, log, delta, priced_step=0)
                    await _mirror_report_cost(session, state, log, delta, priced_step=0)
                    log.cost_usd = cost

            folded_ids = [log.id for log in logs if log.requested_at < state.hourly_folded_through]
            await mirror_request_log_repricing_into_time_rollups(session, folded_ids, reprice)
            await session.commit()
            return BackfillBatch(len(logs), len(logs), logs[-1].id if logs else after_id)
        except BaseException:
            await session.rollback()
            raise


async def _mirror_cost(session: AsyncSession, state: AccountUsageRollupState, log: RequestLog, cost: float) -> None:
    """Mirror a newly priced row (``cost_usd`` NULL -> ``cost``)."""
    await _mirror_lifetime_cost(session, state, log, cost, priced_step=1)
    epoch = epoch_seconds(log.requested_at)
    if log.requested_at < state.hourly_folded_through:
        await session.execute(
            update(RequestUsageHourlyRollup)
            .where(
                RequestUsageHourlyRollup.bucket_epoch == epoch // 3600 * 3600,
                RequestUsageHourlyRollup.account_id == to_dimension(log.account_id),
                RequestUsageHourlyRollup.api_key_id == to_dimension(log.api_key_id),
                RequestUsageHourlyRollup.model == log.model,
                RequestUsageHourlyRollup.service_tier == to_dimension(log.service_tier),
                RequestUsageHourlyRollup.request_kind == log.request_kind,
                RequestUsageHourlyRollup.is_deleted == (log.deleted_at is not None),
            )
            .values(
                cost_usd=RequestUsageHourlyRollup.cost_usd + cost,
                cost_count=RequestUsageHourlyRollup.cost_count + 1,
                priced_requests=case(
                    (RequestUsageHourlyRollup.coverage_unknown == 0, RequestUsageHourlyRollup.priced_requests + 1),
                    else_=RequestUsageHourlyRollup.priced_requests,
                ),
                unpriced_requests=case(
                    (RequestUsageHourlyRollup.coverage_unknown == 0, RequestUsageHourlyRollup.unpriced_requests - 1),
                    else_=RequestUsageHourlyRollup.unpriced_requests,
                ),
            )
        )
        await session.execute(
            update(RequestDemandQuarterRollup)
            .where(
                RequestDemandQuarterRollup.slot_epoch == epoch // 900 * 900,
                RequestDemandQuarterRollup.account_id == to_dimension(log.account_id),
                RequestDemandQuarterRollup.api_key_id == to_dimension(log.api_key_id),
                RequestDemandQuarterRollup.model == log.model,
                RequestDemandQuarterRollup.reasoning_effort == to_dimension(log.reasoning_effort),
                RequestDemandQuarterRollup.request_kind == log.request_kind,
                RequestDemandQuarterRollup.status == log.status,
                RequestDemandQuarterRollup.is_deleted == (log.deleted_at is not None),
            )
            .values(
                cost_usd=RequestDemandQuarterRollup.cost_usd + cost,
                priced_requests=case(
                    (RequestDemandQuarterRollup.coverage_unknown == 0, RequestDemandQuarterRollup.priced_requests + 1),
                    else_=RequestDemandQuarterRollup.priced_requests,
                ),
                unpriced_requests=case(
                    (
                        RequestDemandQuarterRollup.coverage_unknown == 0,
                        RequestDemandQuarterRollup.unpriced_requests - 1,
                    ),
                    else_=RequestDemandQuarterRollup.unpriced_requests,
                ),
            )
        )
    await _mirror_report_cost(session, state, log, cost, priced_step=1)


async def _mirror_lifetime_cost(
    session: AsyncSession, state: AccountUsageRollupState, log: RequestLog, cost: float, *, priced_step: int
) -> None:
    """Add ``cost`` to the lifetime sums; ``priced_step`` moves the row from
    unpriced to priced (1) or leaves its coverage class unchanged (0)."""
    normal = log.request_kind not in _EXCLUDED_KINDS
    if log.requested_at <= state.folded_through and normal:
        if log.api_key_id is not None:
            await session.execute(
                update(ApiKeyUsageRollup)
                .where(
                    ApiKeyUsageRollup.api_key_id == log.api_key_id,
                )
                .values(
                    total_cost_usd=ApiKeyUsageRollup.total_cost_usd + cost,
                    priced_requests=case(
                        (ApiKeyUsageRollup.coverage_unknown == 0, ApiKeyUsageRollup.priced_requests + priced_step),
                        else_=ApiKeyUsageRollup.priced_requests,
                    ),
                    unpriced_requests=case(
                        (ApiKeyUsageRollup.coverage_unknown == 0, ApiKeyUsageRollup.unpriced_requests - priced_step),
                        else_=ApiKeyUsageRollup.unpriced_requests,
                    ),
                )
            )
        if log.account_id is not None and log.deleted_at is None:
            # Only the latest visible duplicate contributes to account lifetime sums.
            latest = await session.scalar(
                select(func.max(RequestLog.id)).where(
                    RequestLog.account_id == log.account_id,
                    RequestLog.request_id == log.request_id,
                    RequestLog.requested_at == log.requested_at,
                    RequestLog.deleted_at.is_(None),
                    RequestLog.request_kind.not_in(_EXCLUDED_KINDS),
                )
            )
            if latest == log.id:
                await session.execute(
                    update(AccountUsageRollup)
                    .where(
                        AccountUsageRollup.account_id == log.account_id,
                    )
                    .values(
                        total_cost_usd=AccountUsageRollup.total_cost_usd + cost,
                        priced_requests=case(
                            (
                                AccountUsageRollup.coverage_unknown == 0,
                                AccountUsageRollup.priced_requests + priced_step,
                            ),
                            else_=AccountUsageRollup.priced_requests,
                        ),
                        unpriced_requests=case(
                            (
                                AccountUsageRollup.coverage_unknown == 0,
                                AccountUsageRollup.unpriced_requests - priced_step,
                            ),
                            else_=AccountUsageRollup.unpriced_requests,
                        ),
                    )
                )


async def _mirror_report_cost(
    session: AsyncSession, state: AccountUsageRollupState, log: RequestLog, cost: float, *, priced_step: int
) -> None:
    normal = log.request_kind not in _EXCLUDED_KINDS
    if log.requested_at < state.reports_folded_through and normal and log.source != "limit_warmup":
        conversation = (log.conversation_id or "").strip(CONVERSATION_WHITESPACE) or None
        epoch = epoch_seconds(log.requested_at)
        await session.execute(
            update(RequestReportHourlyRollup)
            .where(
                RequestReportHourlyRollup.bucket_epoch == epoch // 3600 * 3600,
                RequestReportHourlyRollup.account_id == to_dimension(log.account_id),
                RequestReportHourlyRollup.api_key_id == to_dimension(log.api_key_id),
                RequestReportHourlyRollup.model == log.model,
                RequestReportHourlyRollup.useragent_group == to_dimension(log.useragent_group),
                RequestReportHourlyRollup.conversation_id == to_dimension(conversation),
            )
            .values(
                cost_usd=RequestReportHourlyRollup.cost_usd + cost,
                priced_requests=case(
                    (
                        RequestReportHourlyRollup.coverage_unknown == 0,
                        RequestReportHourlyRollup.priced_requests + priced_step,
                    ),
                    else_=RequestReportHourlyRollup.priced_requests,
                ),
                unpriced_requests=case(
                    (
                        RequestReportHourlyRollup.coverage_unknown == 0,
                        RequestReportHourlyRollup.unpriced_requests - priced_step,
                    ),
                    else_=RequestReportHourlyRollup.unpriced_requests,
                ),
            )
        )
