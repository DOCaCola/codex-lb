"""Manual grant workflow; local settlement and refresh are separate outcomes."""

from datetime import UTC, datetime
from uuid import UUID

from app.db.models import ClaudeResetOperation
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.identity import profile_identity
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.reset_client import ClaimUnknown, ResetClient
from app.modules.claude.reset_repository import ResetRepository, view
from app.modules.claude.reset_schemas import ConsumeGrant, ConsumeView, GrantsView
from app.modules.claude.service import ClaudeService
from app.modules.claude.version import ClaudeVersionService


class ClaudeResets:
    def __init__(self, repository: ClaudeRepository, client: ResetClient | None = None):
        self.repository = repository
        self.client = client or ResetClient()
        self.service = ClaudeService(repository, self.client)
        self.ledger = ResetRepository(repository.session)

    async def _context(self, source_id: str) -> tuple[str, str, str, UUID]:
        snapshot = await self.service.auth.snapshot(source_id)
        version = await ClaudeVersionService(self.repository.session).snapshot()
        token = snapshot.credentials.access_token.get_secret_value()
        profile = await self.client.profile(token, version.version)
        identity = profile_identity(profile)
        account = await self.repository.get(source_id)
        if account is None or account.identity_fingerprint != identity:
            raise ClaudeError("Claude account identity changed")
        try:
            organization = UUID(profile.organization.uuid)
        except ValueError as exc:
            raise ClaudeError("Claude organization identity is invalid") from exc
        await self.repository.session.commit()
        return token, version.version, identity, organization

    async def read(self, source_id: str) -> GrantsView:
        account = await self.service._get(source_id)
        identity = account.identity_fingerprint
        operations = [view(row) for row in await self.ledger.operations(identity)] if identity is not None else []
        await self.repository.session.commit()
        try:
            token, version, _, _ = await self._context(source_id)
            status = await self.client.grants(token, version)
        except ClaudeError:
            return GrantsView(
                status=None, error="Reset grant discovery is unavailable; no balance is assumed.", operations=operations
            )
        return GrantsView(status=status, operations=operations)

    async def consume(self, source_id: str, payload: ConsumeGrant) -> ConsumeView:
        token, version, identity, organization = await self._context(source_id)
        row = await self.repository.session.get(ClaudeResetOperation, str(payload.operation_id))
        # A retry must reach upstream even if the first attempt changed grant availability.
        usable = False
        if row is None:
            status = await self.client.grants(token, version)
            usable = status.usable(payload.grant_id, datetime.now(UTC))
        await self.repository.session.commit()
        row = await self.ledger.begin(source_id, identity, payload, fresh_usable=usable, now=datetime.now(UTC))
        if row.result_json is None:
            operation_id, attempt = row.operation_id, row.attempt
            try:
                answer = await self.client.claim(token, version, organization, payload.grant_id, operation_id)
            except ClaimUnknown:
                await self.ledger.uncertain(source_id, operation_id, attempt)
                return ConsumeView(operation=view(row))
            # Cancellation leaves the durable intent leased; it never permits a fresh-ID retry.
            row = await self.ledger.settle(source_id, operation_id, answer)
        result = ConsumeView(operation=view(row))
        if result.operation.result is not None and result.operation.result.result == "reset":
            try:
                account = await self.service.refresh(source_id, catalog=False)
                result.refresh_complete = account.state.usage_error is None
            except ClaudeError:
                pass  # Redemption is already durably settled, independently of polling.
        return result
