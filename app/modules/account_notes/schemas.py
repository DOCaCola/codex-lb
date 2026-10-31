from __future__ import annotations

from pydantic import Field

from app.modules.account_notes.service import MAX_NOTE_LENGTH
from app.modules.shared.schemas import DashboardModel


class AccountNoteResponse(DashboardModel):
    account_id: str | None
    model_source_id: str | None
    note: str


class AccountNotesResponse(DashboardModel):
    notes: list[AccountNoteResponse]


class AccountNoteUpdate(DashboardModel):
    note: str | None = Field(max_length=MAX_NOTE_LENGTH)
