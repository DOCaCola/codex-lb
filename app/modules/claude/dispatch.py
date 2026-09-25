"""Authorize and prepare one Claude attempt before acquiring transport ownership."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal

from pydantic import JsonValue

from app.core.crypto import TokenEncryptor
from app.db.models import ModelSource
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import RequestProfile, recognize_native
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.request import has_native_identity, project_request
from app.modules.claude.routing import select_account
from app.modules.claude.schemas import CLAUDE_BASE_URL
from app.modules.claude.version import ClaudeVersionService


@dataclass(frozen=True)
class PreparedClaudeRequest:
    source: ModelSource = field(repr=False)
    url: str
    profile: RequestProfile
    headers: dict[str, str] = field(repr=False)
    body: dict[str, JsonValue] = field(repr=False)
    transformations: tuple[str, ...]


class ClaudeDispatchPreparer:
    def __init__(self, repository: ClaudeRepository, client: ClaudeClient | None = None) -> None:
        self.repository = repository
        self.auth = ClaudeAuth(repository, client or ClaudeClient(), TokenEncryptor())

    async def prepare(
        self,
        logical: dict[str, JsonValue],
        api_key: ApiKeyData | None,
        *,
        conversation_id: str,
        incoming_headers: Mapping[str, str],
        endpoint: Literal["messages", "count_tokens"],
        translated: bool,
        owner_source_id: str | None = None,
    ) -> PreparedClaudeRequest:
        model = logical.get("model")
        if not isinstance(model, str) or not model.startswith("anthropic/"):
            raise ClaudeError("Native Claude dispatch requires a selected anthropic/ model")
        if "stream" in logical and not isinstance(logical["stream"], bool):
            raise ClaudeError("Claude stream must be a boolean")
        if endpoint == "count_tokens" and "stream" in logical:
            raise ClaudeError("Claude count_tokens does not support streaming")
        session = self.repository.session
        account = await select_account(
            session,
            model,
            api_key,
            conversation_id=conversation_id,
            owner_source_id=owner_source_id,
            require_streaming=logical.get("stream") is True,
        )
        identity = await ClaudeVersionService(session).snapshot()
        # Authorization and payload validation precede any token refresh.
        native = not translated and recognize_native(
            incoming_headers, version=identity.version, has_identity=has_native_identity(logical)
        )
        profile = RequestProfile.create(
            version=identity.version,
            source_id=account.source_id,
            client_scope=api_key.id if api_key else "anonymous",
            conversation_id=conversation_id,
            native=native,
        )
        body = deepcopy(logical)
        body["model"] = model.removeprefix("anthropic/")
        projected = project_request(body, profile, endpoint=endpoint)
        # Validate caller beta metadata before a potentially rotating grant is
        # touched; the actual token is inserted only after refresh succeeds.
        headers = profile.headers(
            "", endpoint=endpoint, incoming=incoming_headers, feature_betas=projected.feature_betas
        )
        source_id = account.source_id
        credentials = await self.auth.credentials(source_id)
        # A pause or quota refresh may have committed while token
        # rotation was in flight. Re-read instead of using the earlier ORM view.
        session.expire_all()
        account = await select_account(
            session,
            model,
            api_key,
            conversation_id=conversation_id,
            owner_source_id=source_id,
            require_streaming=logical.get("stream") is True,
        )
        headers["authorization"] = f"Bearer {credentials.access_token.get_secret_value()}"
        return PreparedClaudeRequest(
            source=account.source,
            url=CLAUDE_BASE_URL
            + ("/v1/messages?beta=true" if endpoint == "messages" else "/v1/messages/count_tokens?beta=true"),
            profile=profile,
            headers=headers,
            body=projected.body,
            transformations=projected.transformations,
        )
