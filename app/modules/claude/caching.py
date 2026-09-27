"""Cache policy for gateway-owned Responses projections, never native requests."""

from pydantic import JsonValue


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
        block["cache_control"] = {"type": "ephemeral"}
