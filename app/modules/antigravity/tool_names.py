"""Google wire names for translated client tools.

Unlike Anthropic, Google does not fingerprint harness tool names: OmniRoute's
Antigravity tests preserve names and order and forbid a reverse cloak map. Valid
client names therefore pass unchanged. Names outside Gemini's function-name
alphabet (namespaced, long or punctuated) are encoded deterministically and
reversed through the request-local table (opencodex google-wire-compiler.ts).
"""

from __future__ import annotations

import hashlib
import re

from app.modules.claude.tool_names import ClaudeToolNames

_MAX_NAME = 64
_WIRE_NAME = re.compile(rf"[A-Za-z_][A-Za-z0-9_-]{{0,{_MAX_NAME - 1}}}\Z")
_UNSAFE_CHARACTERS = re.compile(r"[^A-Za-z0-9_-]")


def google_wire_name(qualified: str) -> str:
    if _WIRE_NAME.fullmatch(qualified):
        return qualified
    digest = hashlib.sha256(qualified.encode("utf-8", errors="surrogatepass")).hexdigest()[:10]
    safe = _UNSAFE_CHARACTERS.sub("_", qualified)
    if not safe or not (safe[0].isalpha() or safe[0] == "_"):
        safe = "_" + safe
    return safe[: _MAX_NAME - 11] + "_" + digest


class GoogleToolNames(ClaudeToolNames):
    """One request's client tool identities, keyed by the name sent to Google."""

    def wire_base(self, qualified: str) -> str:
        return google_wire_name(qualified)
