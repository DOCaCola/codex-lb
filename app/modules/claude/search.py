"""Hosted search declarations, citations and authenticated replay payloads."""

from copy import deepcopy

from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.credentials import ClaudeError


def search_tool(tool: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    access = tool.get("external_web_access", True)
    if not isinstance(access, bool):
        raise ClientPayloadError("external_web_access must be boolean", param="tools")
    # Deliberate CLIProxyAPI policy: cached-only search is unavailable, not
    # permission to browse live. Keep the rest of the request operational.
    if not access:
        return None
    supported = {"type", "name", "external_web_access", "filters", "user_location", "max_uses"}
    if set(tool) - supported or tool.get("name", "web_search") != "web_search":
        raise ClientPayloadError("Unsupported Claude web search option", param="tools")
    result: dict[str, JsonValue] = {"type": "web_search_20250305", "name": "web_search"}
    if "max_uses" in tool:
        limit = tool["max_uses"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ClientPayloadError("Search max_uses must be a positive integer", param="tools")
        result["max_uses"] = limit
    if "filters" in tool:
        filters = tool["filters"]
        if not isinstance(filters, dict) or set(filters) != {"allowed_domains"}:
            raise ClientPayloadError("Claude search supports only allowed_domains filters", param="tools")
        domains = filters["allowed_domains"]
        if not isinstance(domains, list) or not domains or any(not isinstance(d, str) or not d for d in domains):
            raise ClientPayloadError("Search allowed_domains must be nonempty strings", param="tools")
        result["allowed_domains"] = deepcopy(domains)
    if "user_location" in tool:
        location = tool["user_location"]
        if (
            not isinstance(location, dict)
            or location.get("type") != "approximate"
            or set(location) - {"type", "city", "region", "country", "timezone"}
            or any(not isinstance(v, str) for v in location.values())
        ):
            raise ClientPayloadError("Unsupported search user_location", param="tools")
        result["user_location"] = deepcopy(location)
    return result


def search_replay(block: dict[str, JsonValue]) -> tuple[str, list[JsonValue]]:
    """Validate decoded state; never reconstruct encrypted results from citations."""
    item_id, blocks = block.get("item_id"), block.get("blocks")
    if not isinstance(item_id, str) or not isinstance(blocks, list) or len(blocks) != 2:
        raise ClaudeError("Invalid Claude search replay state")
    call, result = blocks
    if (
        not isinstance(call, dict)
        or call.get("type") != "server_tool_use"
        or call.get("name") != "web_search"
        or not isinstance(call.get("id"), str)
        or not isinstance(result, dict)
        or result.get("type") != "web_search_tool_result"
        or result.get("tool_use_id") != call["id"]
        or not isinstance(result.get("content"), list)
    ):
        raise ClaudeError("Invalid Claude search replay blocks")
    return item_id, deepcopy(blocks)


def url_citations(block: dict[str, JsonValue]) -> list[JsonValue]:
    annotations: list[JsonValue] = []
    text = str(block.get("text", ""))
    citations = block.get("citations", [])
    if not isinstance(citations, list):
        raise ClaudeError("Invalid Claude citations")
    for citation in citations:
        if not isinstance(citation, dict) or citation.get("type") != "web_search_result_location":
            raise ClaudeError("Unsupported Claude citation")
        url, title = citation.get("url"), citation.get("title")
        if not isinstance(url, str) or not isinstance(title, str):
            raise ClaudeError("Invalid Claude URL citation")
        cited = citation.get("cited_text")
        start = text.rfind(cited) if isinstance(cited, str) and cited else -1
        end = start + len(cited) if start >= 0 and isinstance(cited, str) else len(text)
        annotations.append(
            {"type": "url_citation", "url": url, "title": title, "start_index": max(0, start), "end_index": end}
        )
    return annotations
