"""Cache policy for gateway-owned Responses projections, never native requests.

Breakpoints use the 1-hour TTL Claude Code itself sends: agent turns routinely
pause longer than 5 minutes for tool work and review, and a 5-minute entry then
rewrites the whole prefix. Every breakpoint here is gateway-owned and shares one
TTL, so the API's rule that a longer TTL never follows a shorter one holds.

Earlier-turn thinking is kept the same way Claude Code keeps it. By default the
API strips thinking from previous assistant turns, so the replayed prefix
changes whenever a user turn starts and everything after the tools is rewritten.
"""

from pydantic import JsonValue

EXTENDED_CACHE_TTL_BETA = "extended-cache-ttl-2025-04-11"
CONTEXT_MANAGEMENT_BETA = "context-management-2025-06-27"
_BREAKPOINT: dict[str, JsonValue] = {"type": "ephemeral", "ttl": "1h"}
_KEEP_THINKING = {"type": "clear_thinking_20251015", "keep": "all"}


def cache_translated(body: dict[str, JsonValue]) -> None:
    targets: list[dict[str, JsonValue]] = []
    system = body.get("system")
    if isinstance(system, list) and system and isinstance(system[-1], dict):
        targets.append(system[-1])
    else:
        tools = body.get("tools")
        # Deferred tools sit outside the cached prefix and cannot carry a breakpoint.
        prefix = (
            [tool for tool in tools if isinstance(tool, dict) and not tool.get("defer_loading")]
            if isinstance(tools, list)
            else []
        )
        if prefix:
            targets.append(prefix[-1])
    messages = body.get("messages")
    if isinstance(messages, list):
        users: list[dict[str, JsonValue]] = []
        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, list) and content:
                block = content[-1]
                if isinstance(block, dict) and block.get("type") in ("text", "image", "tool_result"):
                    users.append(block)
        targets.extend(users[-2:])
    for block in targets:
        block["cache_control"] = dict(_BREAKPOINT)


def retain_thinking(body: dict[str, JsonValue]) -> bool:
    """Keep earlier-turn thinking; the API rejects the edit unless thinking is on."""
    thinking = body.get("thinking")
    if not isinstance(thinking, dict) or thinking.get("type") not in ("enabled", "adaptive"):
        return False
    body["context_management"] = {"edits": [dict(_KEEP_THINKING)]}
    return True
