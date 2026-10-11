"""Readable bodies for Claude calls to freeform client tools.

A freeform tool is declared to Claude as one `{"input": string}` object. Some models
name that field after its contents (`code`, `cmd`, `patch`) or fence the whole body
in Markdown. For Codex's `exec` and `apply_patch` grammars, the text inside is the
one faithful reading of those shapes (opencodex `apply-patch-envelope.ts`, #4983).
A body with no such reading reaches the tool as the JSON Claude wrote, so the tool's
own error tells the model what went wrong. A complete patch whose outer delimiters are
decorated as `*** Begin Patch ***` gets its delimiters restored; the patch content is
never changed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import JsonValue

PATCH_BEGIN = "*** Begin Patch"
PATCH_END = "*** End Patch"
_PATCH_ENVELOPE = re.compile(
    r"(\*\*\* Begin Patch(?: \*\*\*)?)(\r?\n)(.*)(\r?\n)(\*\*\* End Patch(?: \*\*\*)?)(\r?\n)?", re.DOTALL
)
_PATCH_OPERATION = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: .+$", re.MULTILINE)
_MARKDOWN_FENCE = re.compile(r"```[^\r\n]*\r?\n(.*?)\r?\n```", re.DOTALL)
# Field names a model uses for the body instead of `input`, per grammar.
_FALLBACK_FIELDS: dict[str, tuple[str, ...]] = {
    "exec": ("code", "script", "js", "javascript", "command", "cmd", "content"),
    "apply_patch": ("patch", "content"),
}


@dataclass(frozen=True)
class FreeformBody:
    text: str
    # Content-free labels of every repair applied, in order.
    repairs: tuple[str, ...] = ()


def freeform_grammar(name: str, namespace: str | None) -> str | None:
    """The Codex grammar a bare freeform tool owns; namespaced tools own theirs."""
    return name if namespace is None and name in _FALLBACK_FIELDS else None


def _unfence(text: str, grammar: str | None) -> FreeformBody:
    match = _MARKDOWN_FENCE.fullmatch(text.strip()) if grammar is not None else None
    return FreeformBody(match.group(1), ("markdown_fence",)) if match else FreeformBody(text)


def freeform_body(arguments: dict[str, JsonValue], grammar: str | None) -> FreeformBody:
    """The text a freeform call carries; an empty object is an empty body."""
    if not arguments:
        return FreeformBody("")
    value = arguments.get("input")
    if "input" not in arguments:
        fields = [name for name in _FALLBACK_FIELDS.get(grammar or "", ()) if isinstance(arguments.get(name), str)]
        if len(fields) == 1:
            value = arguments[fields[0]]
            assert isinstance(value, str)
            body = _unfence(value, grammar)
            return FreeformBody(body.text, (f"field_{fields[0]}", *body.repairs))
    if isinstance(value, str):
        return _unfence(value, grammar)
    return FreeformBody(json.dumps(arguments, ensure_ascii=False, separators=(",", ":")), ("unreadable_body",))


def is_patch_envelope(text: str) -> bool:
    """Whether the text is exactly one complete patch that operates on a file."""
    match = _PATCH_ENVELOPE.fullmatch(text)
    return match is not None and _PATCH_OPERATION.search(match.group(3)) is not None


def normalize_patch_delimiters(text: str) -> FreeformBody:
    """Restore decorated outer delimiters of one complete patch; anything else is unchanged."""
    match = _PATCH_ENVELOPE.fullmatch(text)
    if match is None or _PATCH_OPERATION.search(match.group(3)) is None:
        return FreeformBody(text)
    begin, begin_break, body, end_break, end, trailing = match.groups()
    if begin == PATCH_BEGIN and end == PATCH_END:
        return FreeformBody(text)
    return FreeformBody(
        f"{PATCH_BEGIN}{begin_break}{body}{end_break}{PATCH_END}{trailing or ''}", ("patch_delimiters",)
    )
