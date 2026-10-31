from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dashboard_access import Permission
from app.core.auth.dependencies import (
    require_dashboard_permission,
    set_dashboard_error_format,
    validate_dashboard_session,
)
from app.core.exceptions import DashboardNotFoundError
from app.db.session import get_session
from app.modules.account_notes.schemas import AccountNoteResponse, AccountNotesResponse, AccountNoteUpdate
from app.modules.account_notes.service import AccountNoteService

router = APIRouter(
    prefix="/api/account-notes",
    tags=["dashboard"],
    dependencies=[
        Depends(validate_dashboard_session),
        Depends(set_dashboard_error_format),
    ],
)


async def _notes(service: AccountNoteService) -> AccountNotesResponse:
    return AccountNotesResponse(
        notes=[
            AccountNoteResponse(account_id=entry.account_id, model_source_id=entry.model_source_id, note=entry.note)
            for entry in await service.notes()
        ]
    )


@router.get(
    "",
    response_model=AccountNotesResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_READ))],
)
async def list_notes(session: AsyncSession = Depends(get_session)) -> AccountNotesResponse:
    return await _notes(AccountNoteService(session))


@router.put(
    "/accounts/{account_id}",
    response_model=AccountNotesResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_account_note(
    account_id: str,
    payload: AccountNoteUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountNotesResponse:
    service = AccountNoteService(session)
    if not await service.set_account_note(account_id, payload.note):
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return await _notes(service)


@router.put(
    "/model-sources/{source_id}",
    response_model=AccountNotesResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_model_source_note(
    source_id: str,
    payload: AccountNoteUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountNotesResponse:
    service = AccountNoteService(session)
    if not await service.set_model_source_note(source_id, payload.note):
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return await _notes(service)
