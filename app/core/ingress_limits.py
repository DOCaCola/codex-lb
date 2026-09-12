"""HTTP ingress body defaults.

The configured Responses budget is resolved through ``ingress_policy``.
Keep defaults and bounds here independent of Settings to avoid circular imports.
"""

from __future__ import annotations

from typing import Final

# General raw and decompressed request-body budget for every guarded HTTP path.
MAX_DECOMPRESSED_BODY_BYTES: Final[int] = 32 * 1024 * 1024
# Default Responses ingress (including compact): Codex
# clients resend the whole conversation history (inline screenshots included) in
# one request after a reconnect, so this budget is deliberately larger.
MAX_DECOMPRESSED_RESPONSES_BODY_BYTES: Final[int] = 128 * 1024 * 1024
MAX_CONFIGURABLE_RESPONSES_BODY_BYTES: Final[int] = 512 * 1024 * 1024
