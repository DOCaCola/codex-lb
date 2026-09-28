"""Bounded, allowlisted provider diagnostics; never expose raw error metadata."""

import json
import re

import aiohttp

from app.core.runtime_logging import redact_rendered_log_text
from app.core.types import JsonValue

MAX_ERROR_BYTES = 64 * 1024
MAX_ERROR_MESSAGE = 2048
_KEY_TOKEN = re.compile(r"(?i)\bsk[-_][a-z0-9_.*…+/=~-]+")


async def read_error(response: aiohttp.ClientResponse) -> dict[str, JsonValue] | None:
    body = bytearray()
    try:
        async for chunk in response.content.iter_chunked(8192):
            if len(body) + len(chunk) > MAX_ERROR_BYTES:
                return None
            body.extend(chunk)
        data = json.loads(body)
    except (ValueError, RecursionError, aiohttp.ClientError):
        return None
    return data if isinstance(data, dict) else None


def _safe_text(value: JsonValue, secret: str, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    if secret:
        value = value.replace(secret, "[REDACTED]")
    value = _KEY_TOKEN.sub("[REDACTED]", value)
    value = redact_rendered_log_text(value)
    return " ".join(value.split())[:limit]


def normalize_error(payload: dict[str, JsonValue], status: int, *, secret: str = "") -> dict[str, JsonValue]:
    error = payload.get("error")
    if not isinstance(error, dict):
        error = {}
    message = _safe_text(error.get("message"), secret, 1024) or "OpenRouter returned an error"
    code = error.get("code")
    normalized: dict[str, JsonValue] = {
        "message": message,
        "code": str(code) if isinstance(code, int) else _safe_text(code, secret, 128) or None,
        "type": _safe_text(error.get("type"), secret, 128)
        or ("invalid_request_error" if status < 500 else "upstream_error"),
    }
    param = _safe_text(error.get("param"), secret, 128)
    if param:
        normalized["param"] = param
    metadata = error.get("metadata")
    if isinstance(metadata, dict):
        provider = _safe_text(metadata.get("provider_name"), secret, 128)
        raw = metadata.get("raw")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw) if len(raw) <= MAX_ERROR_BYTES else None
            except (ValueError, RecursionError):
                raw = None
        detail = raw.get("error", raw) if isinstance(raw, dict) else None
        if isinstance(detail, dict):
            reason = _safe_text(detail.get("message"), secret, 1024)
            context = []
            for field in ("code", "param"):
                value = detail.get(field)
                value = str(value) if isinstance(value, int) else value
                safe = _safe_text(value, secret, 128)
                if safe:
                    context.append(f"{field}={safe}")
            if reason and reason != message:
                message += f"; {reason}"
            if context:
                message += " (" + ", ".join(context) + ")"
        if provider:
            message += f" [provider: {provider}]"
    normalized["message"] = message[:MAX_ERROR_MESSAGE]
    return {"error": normalized}
