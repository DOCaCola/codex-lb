"""Durable reset intent, leases and first-settlement-wins reconciliation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeAccount, ClaudeResetOperation
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.quota_evidence import lock_account, reconcile_reset
from app.modules.claude.reset_schemas import ClaimAnswer, ConsumeGrant, OperationView

RETRY_WINDOW = timedelta(minutes=10)
LEASE = timedelta(seconds=90)


def view(row: ClaudeResetOperation) -> OperationView:
    return OperationView(
        operation_id=row.operation_id,
        grant_id=row.grant_id,
        created_at=row.created_at.replace(tzinfo=UTC),
        retry_until=row.created_at.replace(tzinfo=UTC) + RETRY_WINDOW,
        lease_until=row.lease_until.replace(tzinfo=UTC),
        result=ClaimAnswer.model_validate_json(row.result_json) if row.result_json else None,
    )


class ResetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def operations(self, identity: str) -> list[ClaudeResetOperation]:
        return list(
            await self.session.scalars(
                select(ClaudeResetOperation)
                .where(ClaudeResetOperation.identity == identity)
                .order_by(ClaudeResetOperation.created_at.desc())
            )
        )

    async def begin(
        self,
        source_id: str,
        identity: str,
        payload: ConsumeGrant,
        *,
        fresh_usable: bool,
        now: datetime,
    ) -> ClaudeResetOperation:
        account = await lock_account(self.session, source_id)
        if account.identity_fingerprint != identity:
            raise ClaudeError("Claude account identity changed")
        timestamp = now.replace(tzinfo=None)
        operation_id = str(payload.operation_id)
        existing = await self.session.get(ClaudeResetOperation, operation_id, populate_existing=True)
        if existing is not None:
            if existing.identity != identity or existing.grant_id != payload.grant_id:
                raise ClaudeError("Reset operation identity mismatch")
            if existing.result_json is not None:
                await self.session.commit()
                return existing
            if existing.lease_until > timestamp:
                raise ClaudeError("Reset operation is still in flight")
            if timestamp >= existing.created_at + RETRY_WINDOW:
                raise ClaudeError("Uncertain reset retry window expired; review before a new spend")
        others = await self.operations(identity)
        for other in others:
            if other.operation_id == operation_id or other.result_json is not None:
                continue
            if other.lease_until > timestamp or timestamp < other.created_at + RETRY_WINDOW:
                raise ClaudeError("An unresolved reset operation must be retried with its original ID")
            if existing is None and not payload.acknowledge_uncertain:
                raise ClaudeError("A previous reset outcome is unknown; explicit risk acknowledgement is required")
        if existing is None:
            if not fresh_usable:
                raise ClaudeError("Reset grant is not currently usable")
            existing = ClaudeResetOperation(
                operation_id=operation_id,
                source_id=source_id,
                identity=identity,
                grant_id=payload.grant_id,
                created_at=timestamp,
                lease_until=timestamp + LEASE,
                attempt=1,
            )
            self.session.add(existing)
        else:
            existing.attempt += 1
            existing.lease_until = timestamp + LEASE
        await self.session.commit()
        return existing

    async def uncertain(self, source_id: str, operation_id: str, attempt: int) -> None:
        await lock_account(self.session, source_id)
        row = await self.session.get(ClaudeResetOperation, operation_id, populate_existing=True)
        if row is not None and row.result_json is None and row.attempt == attempt:
            row.lease_until = datetime.now(UTC).replace(tzinfo=None)
        await self.session.commit()

    async def settle(
        self,
        source_id: str,
        operation_id: str,
        answer: ClaimAnswer,
    ) -> ClaudeResetOperation:
        account: ClaudeAccount = await lock_account(self.session, source_id)
        row = await self.session.get(ClaudeResetOperation, operation_id, populate_existing=True)
        if row is None or row.identity != account.identity_fingerprint:
            raise ClaudeError("Reset settlement identity unavailable; outcome remains unknown")
        if row.result_json is None:
            row.result_json = answer.model_dump_json()
            row.lease_until = datetime.now(UTC).replace(tzinfo=None)
            if answer.result == "reset":
                # Same-ID retries may replay the original reset. Never advance
                # the barrier to a retry's start and erase post-reset evidence.
                await reconcile_reset(self.session, account, answer.cleared, row.created_at.replace(tzinfo=UTC))
        await self.session.commit()
        return row
