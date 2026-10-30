"""The native CLI's search_web tool, executed by the gateway on the dispatching account.

Gemini on Cloud Code has no hosted search a Codex client can rely on. The Antigravity CLI declares
a `search_web` function and answers each call with a separate non-streaming `web_search` request on
the same account (agy 1.4.10 capture): Google Search grounding on the catalog's search model, then
the grounded summary with numbered sources as the function result. The gateway does the same and
shows the call to the client as a hosted `web_search_call`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.modules.antigravity.classify import classify
from app.modules.antigravity.client import CloudCodeClient
from app.modules.antigravity.errors import AntigravityError, MetadataHTTPError
from app.modules.antigravity.version import ClientIdentity

logger = logging.getLogger(__name__)

SEARCH_TOOL_NAME = "search_web"
# Searches one response may run before further calls are answered with an error; Codex sets no limit.
DEFAULT_MAX_USES = 8
_DECLARATION: dict[str, JsonValue] = {
    "name": SEARCH_TOOL_NAME,
    "description": (
        "Performs a web search for a given query. Returns a summary of relevant information along with URL citations."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "domain": {"type": "STRING", "description": "Optional domain to recommend the search prioritize"},
            "query": {"type": "STRING"},
        },
        "required": ["query"],
    },
}
_SYSTEM = (
    "You are a search engine bot. You will be given a query from a user. Your task is to search the web for "
    "relevant information that will help the user. You MUST perform a web search. Do not respond or interact "
    "with the user, please respond as if they typed the query into a search bar."
)
_NOTE = "Note: Source URLs are HTTP redirects; check where they resolve if you need the direct link."


def search_declaration() -> dict[str, JsonValue]:
    return {**_DECLARATION}


@dataclass(frozen=True)
class SearchPolicy:
    """The client's web_search tool: domains it allows and the per-response search limit."""

    domains: tuple[str, ...] = ()
    max_uses: int = DEFAULT_MAX_USES


def search_policy(tool: dict[str, JsonValue], *, param: str) -> SearchPolicy | None:
    """The client's hosted search tool; cached-only search is unavailable, not live browsing (CLIProxyAPI)."""
    access = tool.get("external_web_access", True)
    if not isinstance(access, bool):
        raise ClientPayloadError("external_web_access must be boolean", param=param)
    if not access:
        return None
    if set(tool) - {"type", "external_web_access", "filters", "max_uses"}:
        raise ClientPayloadError("Unsupported Antigravity web search option", param=param)
    domains: tuple[str, ...] = ()
    if "filters" in tool:
        filters = tool["filters"]
        allowed = (
            filters.get("allowed_domains")
            if isinstance(filters, dict) and set(filters) == {"allowed_domains"}
            else None
        )
        domains = tuple(d for d in allowed if isinstance(d, str) and d) if isinstance(allowed, list) else ()
        if not domains or len(domains) != len(cast(list[JsonValue], allowed)):
            raise ClientPayloadError("Antigravity web search supports only nonempty allowed_domains", param=param)
    limit = tool.get("max_uses", DEFAULT_MAX_USES)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ClientPayloadError("Search max_uses must be a positive integer", param=param)
    return SearchPolicy(domains, limit)


class SealedSearch(BaseModel):
    """One answered search_web call, replayed as its call and function response."""

    item_id: str
    call_id: str
    args: dict[str, JsonValue]
    response: dict[str, JsonValue]


@dataclass(frozen=True)
class SearchCall:
    item_id: str
    call_id: str
    args: dict[str, JsonValue]

    @property
    def query(self) -> str:
        query = self.args["query"]
        assert isinstance(query, str)
        return query


@dataclass(frozen=True)
class SearchOutcome:
    call: SearchCall
    response: dict[str, JsonValue]
    succeeded: bool

    def sealed(self) -> SealedSearch:
        return SealedSearch(
            item_id=self.call.item_id, call_id=self.call.call_id, args=self.call.args, response=self.response
        )


@dataclass(frozen=True)
class SearchContext:
    """What a search needs from the prepared request: the same account, project and client identity."""

    model: str
    project_id: str
    access_token: str
    identity: ClientIdentity
    policy: SearchPolicy
    source_id: str


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _included_domains(policy: SearchPolicy, domain: JsonValue) -> list[str]:
    if policy.domains:
        return [domain] if isinstance(domain, str) and domain in policy.domains else list(policy.domains)
    return [domain] if isinstance(domain, str) and domain else []


def search_envelope(context: SearchContext, call: SearchCall) -> dict[str, JsonValue]:
    """The CLI's web_search request; key order follows the capture."""
    google_search: dict[str, JsonValue] = {"enhancedContent": {"imageSearch": {"maxResultCount": 5}}}
    domains = _included_domains(context.policy, call.args.get("domain"))
    if domains:
        google_search["includedDomains"] = list(domains)
    return {
        "project": context.project_id,
        "request": {
            "contents": [{"role": "user", "parts": [{"text": call.query}]}],
            "systemInstruction": {"role": "user", "parts": [{"text": _SYSTEM}]},
            "tools": [{"googleSearch": google_search}],
            "generationConfig": {"candidateCount": 1},
        },
        "model": context.model,
        "userAgent": "antigravity",
        "requestType": "web_search",
    }


def _invalid() -> AntigravityError:
    return AntigravityError("Antigravity returned an invalid web search response", code="invalid_upstream_response")


def summary(query: str, data: dict[str, JsonValue], created: datetime, completed: datetime) -> str:
    """The grounded answer with numbered citation markers and its sources, as the CLI hands it to the model."""
    response = data.get("response")
    candidates = response.get("candidates") if isinstance(response, dict) else None
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
        raise _invalid()
    candidate = candidates[0]
    content = candidate.get("content")
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise _invalid()
    texts: list[str] = []
    for part in parts:
        piece = part.get("text") if isinstance(part, dict) else None
        if isinstance(piece, str) and isinstance(part, dict) and part.get("thought") is not True:
            texts.append(piece)
    text = "".join(texts)
    grounding = candidate.get("groundingMetadata")
    chunks = grounding.get("groundingChunks", []) if isinstance(grounding, dict) else []
    supports = grounding.get("groundingSupports", []) if isinstance(grounding, dict) else []
    if not isinstance(chunks, list) or not isinstance(supports, list):
        raise _invalid()
    sources: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        web = chunk.get("web") if isinstance(chunk, dict) else None
        if not isinstance(web, dict) or not isinstance(uri := web.get("uri"), str):
            raise _invalid()
        title = web.get("title") or web.get("domain") or uri
        sources.append(f"[{index}] [{title}]({uri})")
    # Segment offsets are UTF-8 byte offsets; markers go in from the end so earlier offsets stay valid.
    encoded = text.encode()
    markers: list[tuple[int, str]] = []
    for support in supports:
        segment = support.get("segment") if isinstance(support, dict) else None
        end = segment.get("endIndex") if isinstance(segment, dict) else None
        indices = support.get("groundingChunkIndices") if isinstance(support, dict) else None
        if not isinstance(end, int) or not 0 <= end <= len(encoded) or not isinstance(indices, list):
            raise _invalid()
        numbers = [i for i in indices if isinstance(i, int) and 0 <= i < len(chunks)]
        if len(numbers) != len(indices):
            raise _invalid()
        markers.append((end, "".join(f"[{i + 1}]" for i in numbers)))
    for end, marker in sorted(markers, key=lambda entry: entry[0], reverse=True):
        encoded = encoded[:end] + marker.encode() + encoded[end:]
    body = encoded.decode(errors="replace")
    lines = [
        f"Created At: {_stamp(created)}",
        f"Completed At: {_stamp(completed)}",
        f'The search for "{query}" returned the following summary:',
        body,
        "",
    ]
    if sources:
        lines.extend(["Sources:", *sources, ""])
    lines.append(_NOTE)
    return "\n".join(lines)


def failure(created: datetime, completed: datetime, message: str) -> dict[str, JsonValue]:
    """A failed call's function response, worded as the CLI reports tool errors."""
    return {
        "error": "\n".join(
            [
                f"Created At: {_stamp(created)}",
                f"Completed At: {_stamp(completed)}",
                f"Encountered error in tool execution: {message}",
            ]
        )
    }


async def run_search(context: SearchContext, call: SearchCall, *, allowed: bool) -> SearchOutcome:
    """Run one call; failures become the model's tool error, as in the CLI, and never end the response."""
    created = datetime.now(UTC)
    if not allowed:
        message = f"web search limit of {context.policy.max_uses} searches reached for this response"
        return SearchOutcome(call, failure(created, created, message), False)
    try:
        data = await CloudCodeClient(context.identity).call(
            "generateContent", context.access_token, search_envelope(context, call)
        )
        output = summary(call.query, data, created, datetime.now(UTC))
    except MetadataHTTPError as exc:
        message = classify(exc.status, exc.body).message
        logger.info(
            "antigravity_web_search source_id=%s model=%s status=%d", context.source_id, context.model, exc.status
        )
        return SearchOutcome(call, failure(created, datetime.now(UTC), message), False)
    except AntigravityError as exc:
        logger.info("antigravity_web_search source_id=%s model=%s error=%s", context.source_id, context.model, exc.code)
        return SearchOutcome(call, failure(created, datetime.now(UTC), str(exc)), False)
    logger.info("antigravity_web_search source_id=%s model=%s status=200", context.source_id, context.model)
    return SearchOutcome(call, {"output": output}, True)
