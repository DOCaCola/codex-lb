from __future__ import annotations

from app.modules.account_colors.service import PALETTE_SIZE, ColorMember, resolve_colors


def _members(*picks: int | None) -> list[ColorMember]:
    return [ColorMember(f"acc_{index}", None, pick) for index, pick in enumerate(picks)]


def test_automatic_accounts_take_palette_in_creation_order() -> None:
    resolved = resolve_colors(_members(None, None, None))
    assert [entry.color for entry in resolved] == [0, 1, 2]
    assert [entry.automatic_color for entry in resolved] == [0, 1, 2]


def test_picks_win_and_automatic_accounts_skip_picked_colours() -> None:
    resolved = resolve_colors(_members(None, 0, None))
    assert [entry.color for entry in resolved] == [1, 0, 2]
    # Without its pick the second account would take the first colour left free.
    assert resolved[1].automatic_color == 1
    assert resolved[1].chart_color == 0


def test_automatic_assignment_cycles_once_the_palette_is_exhausted() -> None:
    resolved = resolve_colors(_members(*([None] * (PALETTE_SIZE + 2))))
    assert [entry.color for entry in resolved][-3:] == [PALETTE_SIZE - 1, 0, 1]
