"""OAuth wire profile, independent of enrollment and transport ownership.

Compatibility recognition is not authentication. Callers must already have passed
source authorization before using this module. No caller credentials are forwarded.
"""

from __future__ import annotations

import platform
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.modules.claude.credentials import ClaudeError

PROFILE_REVISION = "claude-oauth-v3"
CLI_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
OAUTH_BETA = "oauth-2025-04-20"
CLI_BETA = "claude-code-20250219"
MID_SYSTEM_BETA = "mid-conversation-system-2026-04-07"
# Claude Code surfaces whose request shape has been captured (CLIProxyAPI's native set).
_NATIVE_ENTRYPOINTS = frozenset({"cli", "sdk-cli", "sdk-ts", "claude-vscode"})
# `cli-bg` marks `claude --bg` background sessions (CLIProxyAPI #7412).
_NATIVE_X_APPS = frozenset({"cli", "cli-bg"})
_UA_PRODUCT = re.compile(r"^claude-cli/(\d+)\.(\d+)\.(\d+)$")
_UA_FIELD_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_PACKAGE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_BETA = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_NATIVE_HEADERS = frozenset(
    {
        "user-agent",
        "x-app",
        "anthropic-version",
        "anthropic-dangerous-direct-browser-access",
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


@dataclass(frozen=True)
class ClientBuild:
    """A verified Claude Code release: its CLI, Stainless SDK and runtime versions occur only together."""

    version: str
    sdk_version: str
    runtime_version: str


def management_headers(token: str, version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": OAUTH_BETA,
        "User-Agent": f"claude-cli/{version} (external, cli)",
        "x-app": "cli",
        "Accept": "application/json",
    }


def _native_client_version(user_agent: str) -> tuple[int, int, int] | None:
    """Version of a native Claude Code user agent.

    Claude Code appends ``name/value`` fields after its entrypoint (``agent-sdk/``,
    ``client-app/``, ``workload/cron``); their values are opaque request context
    (CLIProxyAPI #7373).
    """
    product, separator, comment = user_agent.partition(" (")
    match = _UA_PRODUCT.fullmatch(product)
    if match is None or not separator or not comment.endswith(")") or not user_agent.isprintable():
        return None
    inner = comment[:-1]
    if "(" in inner or ")" in inner:
        return None
    fields = [field.strip() for field in inner.split(",")]
    if len(fields) < 2 or fields[0] != "external" or fields[1] not in _NATIVE_ENTRYPOINTS:
        return None
    names: set[str] = set()
    for field in fields[2:]:
        name, slash, value = field.partition("/")
        if not slash or not value or not _UA_FIELD_NAME.fullmatch(name) or name.lower() in names:
            return None
        if name.lower() == "agent-sdk" and not _PACKAGE_VERSION.fullmatch(value):
            return None
        names.add(name.lower())
    return int(match[1]), int(match[2]), int(match[3])


def recognize_native(headers: Mapping[str, str], *, version: str, has_identity: bool) -> bool:
    """Recognize genuine Claude Code in either token mode; newer patches keep their own profile.

    Claude Code sends ``claude-code-20250219`` whether it holds an OAuth token or an
    API key; only its subscription mode adds the OAuth beta, which its markerless
    helpers carry alone.
    """
    values = {key.lower(): value for key, value in headers.items()}
    client = _native_client_version(values.get("user-agent", ""))
    if client is None or not has_identity or values.get("x-app") not in _NATIVE_X_APPS:
        return False
    major, minor, patch = map(int, version.split("."))
    betas = _betas(values.get("anthropic-beta", ""))
    return (
        client[:2] == (major, minor)
        and client[2] >= patch
        and (CLI_BETA in betas or OAUTH_BETA in betas)
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
    build: ClientBuild
    session_id: str
    request_id: str
    native: bool
    revision: str = PROFILE_REVISION

    @property
    def version(self) -> str:
        return self.build.version

    @classmethod
    def create(
        cls, *, build: ClientBuild, source_id: str, client_scope: str, conversation_id: str, native: bool
    ) -> RequestProfile:
        # Length-prefix the components so account/scope/conversation boundaries
        # cannot collide. Tokens do not participate in this durable identity.
        return cls(build, session_identity(source_id, client_scope, conversation_id), str(uuid4()), native)

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
                    "x-stainless-package-version": self.build.sdk_version,
                    "x-stainless-runtime": "node",
                    "x-stainless-runtime-version": self.build.runtime_version,
                    "x-stainless-os": {"Darwin": "MacOS"}.get(platform.system(), platform.system()),
                    "x-stainless-arch": {"aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}.get(
                        platform.machine(), platform.machine()
                    ),
                    "anthropic-dangerous-direct-browser-access": "true",
                }
            )
        if endpoint == "messages":
            result.setdefault("x-stainless-timeout", "600")
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
