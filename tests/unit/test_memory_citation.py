from __future__ import annotations

import pytest

from app.core.openai.memory_citation import CLOSE, OPEN, MemoryCitationEscaper, escape_memory_citation_mentions

ENTRIES = "<citation_entries>\nMEMORY.md:1-2|note=[x]\n</citation_entries>\n<rollout_ids>\nid-1\n</rollout_ids>"
REAL_BLOCK = f"{OPEN}\n{ENTRIES}\n{CLOSE}"
SAMPLES = [
    f"Put the `{OPEN}` block at the very end. The rest of this answer must stay visible.",
    f"Answer first.\n{REAL_BLOCK}",
    f"Mention `{OPEN}` early, then cite.\n{REAL_BLOCK}",
    f"A stray {CLOSE} closes nothing, and <b>other</b> tags < stay.",
    f"Ends on an undecided tag {OPEN}  ",
    "Ends on a partial tag <oai-mem",
]


def _visible(text: str) -> str:
    return text.replace("\u2060", "")


def test_a_quoted_tag_is_neutralized_and_the_rest_survives() -> None:
    escaped = escape_memory_citation_mentions(SAMPLES[0])
    assert OPEN not in escaped
    assert _visible(escaped) == SAMPLES[0]


def test_a_real_citation_block_stays_verbatim() -> None:
    assert escape_memory_citation_mentions(SAMPLES[1]) == SAMPLES[1]


def test_a_mention_before_a_real_block_is_neutralized_and_the_block_kept() -> None:
    escaped = escape_memory_citation_mentions(SAMPLES[2])
    assert escaped.endswith(REAL_BLOCK)
    assert escaped.count(OPEN) == 1
    assert _visible(escaped) == SAMPLES[2]


@pytest.mark.parametrize("sample", SAMPLES[3:])
def test_stray_and_unfinished_tags_are_neutralized(sample: str) -> None:
    escaped = escape_memory_citation_mentions(sample)
    assert OPEN not in escaped and CLOSE not in escaped
    assert _visible(escaped) == sample


@pytest.mark.parametrize("sample", SAMPLES)
def test_chunking_does_not_change_the_result(sample: str) -> None:
    whole = escape_memory_citation_mentions(sample)
    for split in range(len(sample) + 1):
        escaper = MemoryCitationEscaper()
        assert escaper.push(sample[:split]) + escaper.push(sample[split:]) + escaper.flush() == whole
    escaper = MemoryCitationEscaper()
    assert "".join(escaper.push(char) for char in sample) + escaper.flush() == whole
