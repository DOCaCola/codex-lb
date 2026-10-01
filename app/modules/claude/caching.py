"""Cache policy for gateway-owned Responses projections, never native requests.

Breakpoints use the 1-hour TTL Claude Code itself sends: agent turns routinely
pause longer than 5 minutes for tool work and review, and a 5-minute entry then
rewrites the whole prefix. Every breakpoint here is gateway-owned and shares one
TTL, so the API's rule that a longer TTL never follows a shorter one holds.
"""

from pydantic import JsonValue

EXTENDED_CACHE_TTL_BETA = "extended-cache-ttl-2025-04-11"
_BREAKPOINT: dict[str, JsonValue] = {"type": "ephemeral", "ttl": "1h"}


def cache_translated(body: dict[str, JsonValue]) -> None:
    targets: list[dict[str, JsonValue]] = []
    system = body.get("system")
    if isinstance(system, list) and system and isinstance(system[-1], dict):
        targets.append(system[-1])
    else:
        tools = body.get("tools")
        if isinstance(tools, list) and tools and isinstance(tools[-1], dict):
            targets.append(tools[-1])
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
