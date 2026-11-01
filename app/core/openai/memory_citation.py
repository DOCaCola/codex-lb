"""Neutralize prose mentions of the Codex client's memory-citation tag in generated answer text.

Codex parses the memory-citation tag in assistant text as markup, not as Markdown: it hides the
tagged span, and when no closing tag follows it hides everything after the opening tag. A model
that merely quotes the tag therefore loses the rest of its answer (opencodex #8044).

A real citation block opens with the citation-entries element and stays verbatim, so Codex
memories still render. Every other tag gets a word joiner after its "<": the text looks the same
in prose and in code spans, and the client no longer matches it as markup.
"""

from __future__ import annotations

OPEN = "<oai-mem-citation>"
CLOSE = "</oai-mem-citation>"
_BODY_OPEN = "<citation_entries>"
_WORD_JOINER = "\u2060"


def _neutralized(tag: str) -> str:
    return "<" + _WORD_JOINER + tag[1:]


class MemoryCitationEscaper:
    """Streaming escaper for one text part.

    A tag can arrive split across deltas, and whether an opening tag starts a real block depends on
    what follows it, so undecidable text is held until the next delta or ``flush``. The output is
    the same however the text is chunked.
    """

    def __init__(self) -> None:
        self._held = ""
        self._in_block = False

    def push(self, delta: str) -> str:
        text = self._held + delta
        self._held = ""
        out: list[str] = []
        position = 0
        while (at := text.find("<", position)) >= 0:
            out.append(text[position:at])
            tail = text[at:]
            if tail.startswith(CLOSE):
                out.append(CLOSE if self._in_block else _neutralized(CLOSE))
                self._in_block = False
                position = at + len(CLOSE)
            elif tail.startswith(OPEN):
                follower = tail[len(OPEN) :].lstrip()
                if not self._in_block and (not follower or _BODY_OPEN.startswith(follower)):
                    self._held = tail
                    return "".join(out)
                real = not self._in_block and follower.startswith(_BODY_OPEN)
                out.append(OPEN if real else _neutralized(OPEN))
                self._in_block = self._in_block or real
                position = at + len(OPEN)
            elif OPEN.startswith(tail) or CLOSE.startswith(tail):
                self._held = tail
                return "".join(out)
            else:
                out.append("<")
                position = at + 1
        out.append(text[position:])
        return "".join(out)

    def flush(self) -> str:
        """Release held text at the end of the part; an opening tag still undecided starts no block."""
        held, self._held = self._held, ""
        if held.startswith(OPEN):
            return _neutralized(OPEN) + held[len(OPEN) :]
        return held


def escape_memory_citation_mentions(text: str) -> str:
    escaper = MemoryCitationEscaper()
    return escaper.push(text) + escaper.flush()
