"""One physical claim; transport ambiguity never means unspent."""

from uuid import UUID

import aiohttp
from pydantic import ValidationError

from app.core.clients.http import lease_model_source_session
from app.modules.claude.client import ClaudeClient, bounded_body
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import management_headers
from app.modules.claude.reset_schemas import ClaimAnswer, GrantEnvelope, GrantStatus
from app.modules.claude.schemas import CLAUDE_BASE_URL


class ClaimUnknown(ClaudeError):
    pass


class ResetClient(ClaudeClient):
    async def grants(self, token: str, version: str) -> GrantStatus:
        response = await self._get("/api/oauth/usage?cedar_ember=1&skip_spend=1", token, version, GrantEnvelope)
        return response.cedar_ember

    async def claim(
        self, token: str, version: str, organization: UUID, grant_id: str, operation_id: str
    ) -> ClaimAnswer:
        try:
            async with lease_model_source_session() as session:
                async with session.post(
                    f"{CLAUDE_BASE_URL}/api/organizations/{organization}/reset_rate_limits",
                    headers=management_headers(token, version),
                    json={"program": "cedar_ember", "grant_id": grant_id, "request_id": operation_id},
                    timeout=aiohttp.ClientTimeout(total=25, connect=10),
                    allow_redirects=False,
                ) as response:
                    if response.status in (401, 403):
                        return ClaimAnswer(result="auth_error")
                    if response.status == 429:
                        return ClaimAnswer(result="rate_limited")
                    if response.status != 200:
                        raise ClaimUnknown("Reset outcome is unknown")
                    raw = await bounded_body(response)
                    return ClaimAnswer.model_validate_json(raw)
        except (aiohttp.ClientError, TimeoutError, ValidationError, ClaudeError) as exc:
            raise ClaimUnknown("Reset outcome is unknown") from exc
