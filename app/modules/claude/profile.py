"""OAuth wire profile, independent of enrollment and transport ownership.

Compatibility recognition is not authentication. Callers must already have passed
source authorization before using this module. No caller credentials are forwarded.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.modules.claude.credentials import ClaudeError

PROFILE_REVISION = "claude-oauth-v2"
CLI_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
OAUTH_BETA = "oauth-2025-04-20"
CLI_BETA = "claude-code-20250219"
MID_SYSTEM_BETA = "mid-conversation-system-2026-04-07"
SDK_VERSION = "0.112.1"
RUNTIME_VERSION = "v26.3.0"
_NATIVE_UA = re.compile(r"^claude-cli/(\d+)\.(\d+)\.(\d+) \(external, cli\)$")
_BETA = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_NATIVE_HEADERS = frozenset(
    {
        "user-agent",
        "x-app",
        "anthropic-version",
        "x-stainless-lang",
        "x-stainless-package-version",
        "x-stainless-runtime",
        "x-stainless-runtime-version",
        "x-stainless-os",
        "x-stainless-arch",
        "x-stainless-timeout",
        "x-stainless-helper-method",
        "x-stainless-async",
        "x-stainless-retry-count",
        "x-client-request-id",
        "x-claude-code-agent-id",
        "x-claude-code-parent-agent-id",
        "x-claude-code-request-class",
        "x-claude-code-agent-type",
        "x-claude-code-prev-tool-durations",
        "x-claude-code-compaction",
        "x-claude-code-context-compacted",
    }
)


def management_headers(token: str, version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": OAUTH_BETA,
        "User-Agent": f"claude-cli/{version} (external, cli)",
        "x-app": "cli",
        "Accept": "application/json",
    }


def recognize_native(headers: Mapping[str, str], *, version: str, has_identity: bool) -> bool:
    """Accept newer native patch releases without learning their global profile."""
    values = {key.lower(): value for key, value in headers.items()}
    match = _NATIVE_UA.fullmatch(values.get("user-agent", ""))
    if match is None or not has_identity or values.get("x-app") != "cli":
        return False
    major, minor, patch = map(int, version.split("."))
    return (
        (int(match[1]), int(match[2])) == (major, minor)
        and int(match[3]) >= patch
        and OAUTH_BETA in _betas(values.get("anthropic-beta", ""))
        and values.get("x-stainless-lang") == "js"
    )


def _betas(value: str) -> list[str]:
    result = [item.strip() for item in value.split(",") if item.strip()]
    if len(result) > 32 or any(not _BETA.fullmatch(item) for item in result):
        raise ClaudeError("Invalid Anthropic beta metadata")
    return result


def session_identity(source_id: str, client_scope: str, conversation_id: str) -> str:
    components = (source_id, client_scope, conversation_id)
    seed = "codex-lb:claude:" + "".join(f"{len(value)}:{value}" for value in components)
    return str(uuid5(NAMESPACE_URL, seed))


@dataclass(frozen=True)
class RequestProfile:
    version: str
    session_id: str
    request_id: str
    native: bool
    revision: str = PROFILE_REVISION

    @classmethod
    def create(
        cls, *, version: str, source_id: str, client_scope: str, conversation_id: str, native: bool
    ) -> RequestProfile:
        # Length-prefix the components so account/scope/conversation boundaries
        # cannot collide. Tokens do not participate in this durable identity.
        return cls(version, session_identity(source_id, client_scope, conversation_id), str(uuid4()), native)

    def headers(
        self,
        token: str,
        *,
        endpoint: Literal["messages", "count_tokens"],
        incoming: Mapping[str, str],
        feature_betas: tuple[str, ...] = (),
        stream: bool = False,
    ) -> dict[str, str]:
        result = {key.lower(): value for key, value in management_headers(token, self.version).items()}
        values = {key.lower(): value for key, value in incoming.items()}
        if self.native:
            result.update({key: value for key, value in values.items() if key in _NATIVE_HEADERS})
        else:
            result.update(
                {
                    "x-stainless-lang": "js",
                    "x-stainless-package-version": SDK_VERSION,
                    "x-stainless-runtime": "node",
                    "x-stainless-runtime-version": RUNTIME_VERSION,
                    "x-stainless-os": "Linux",
                    "x-stainless-arch": "x64",
                }
            )
        if endpoint == "messages":
            result.setdefault("x-stainless-timeout", "600")
            if stream and not self.native:
                result["x-stainless-helper-method"] = "stream"
        result.setdefault("x-client-request-id", self.request_id)
        result.setdefault("x-stainless-retry-count", "0")
        betas = _betas(values.get("anthropic-beta", ""))
        betas.append(OAUTH_BETA)
        if endpoint == "messages" and not self.native:
            betas.append(CLI_BETA)
        elif endpoint == "count_tokens":
            betas.append("token-counting-2024-11-01")
        # Caller feature negotiation survives; arbitrary caller headers do not.
        betas.extend(_betas(",".join(feature_betas)))
        result.update(
            {
                "anthropic-beta": ",".join(dict.fromkeys(betas)),
                "content-type": "application/json",
                "x-claude-code-session-id": self.session_id,
            }
        )
        return result
