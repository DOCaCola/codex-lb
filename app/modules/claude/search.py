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


def assistant_history_message(text: str) -> dict[str, JsonValue]:
    """Readable history where provider state cannot travel."""
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


def _search_text(action: str, sources: list[tuple[str | None, str]]) -> str:
    lines = [action]
    if sources:
        lines.append("Sources:")
        lines.extend(f"- {title} — {url}" if title else f"- {url}" for title, url in sources)
    return "\n".join(lines)


def claude_search_text(blocks: list[JsonValue]) -> str:
    """Readable query and results of validated Claude search blocks; no encrypted content."""
    call, result = blocks
    assert isinstance(call, dict) and isinstance(result, dict)
    arguments = call.get("input")
    query = arguments.get("query") if isinstance(arguments, dict) else None
    content = result["content"]
    assert isinstance(content, list)
    sources = [
        (title if isinstance(title := entry.get("title"), str) and title else None, url)
        for entry in content
        if isinstance(entry, dict)
        and entry.get("type") == "web_search_result"
        and isinstance(url := entry.get("url"), str)
    ]
    return _search_text(f"Web search: {query}" if isinstance(query, str) and query else "Web search", sources)


def openai_search_text(item: dict[str, JsonValue]) -> str:
    """Readable form of a Responses `web_search_call` action as Codex serializes it."""
    action = item.get("action")
    action = action if isinstance(action, dict) else {}
    kind = action.get("type")
    url = value if isinstance(value := action.get("url"), str) and value else None
    pattern = value if isinstance(value := action.get("pattern"), str) and value else None
    if kind == "open_page":
        line = f"Opened page: {url}" if url else "Opened page"
    elif kind == "find_in_page":
        line = "Found in page" + (f" {url}" if url else "") + (f": {pattern}" if pattern else "")
    else:
        query, queries = action.get("query"), action.get("queries")
        terms = (
            [query]
            if isinstance(query, str) and query
            else [term for term in queries if isinstance(term, str) and term]
            if isinstance(queries, list)
            else []
        )
        line = f"Web search: {'; '.join(terms)}" if terms else "Web search"
    raw_sources = action.get("sources")
    sources = [
        (title if isinstance(title := source.get("title"), str) and title else None, source_url)
        for source in (raw_sources if isinstance(raw_sources, list) else [])
        if isinstance(source, dict) and isinstance(source_url := source.get("url"), str)
    ]
    return _search_text(line, sources)


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
