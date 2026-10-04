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
from app.modules.account_colors.schemas import AccountColorResponse, AccountColorsResponse, AccountColorUpdate
from app.modules.account_colors.service import AccountColorService

router = APIRouter(
    prefix="/api/account-colors",
    tags=["dashboard"],
    dependencies=[
        Depends(validate_dashboard_session),
        Depends(set_dashboard_error_format),
    ],
)


async def _colors(service: AccountColorService) -> AccountColorsResponse:
    return AccountColorsResponse(
        colors=[
            AccountColorResponse(
                account_id=entry.account_id,
                model_source_id=entry.model_source_id,
                chart_color=entry.chart_color,
                color=entry.color,
                automatic_color=entry.automatic_color,
            )
            for entry in await service.colors()
        ]
    )


@router.get(
    "",
    response_model=AccountColorsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_READ))],
)
async def list_colors(session: AsyncSession = Depends(get_session)) -> AccountColorsResponse:
    return await _colors(AccountColorService(session))


@router.put(
    "/accounts/{account_id}",
    response_model=AccountColorsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_account_color(
    account_id: str,
    payload: AccountColorUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountColorsResponse:
    service = AccountColorService(session)
    if not await service.set_account_color(account_id, payload.chart_color):
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return await _colors(service)


@router.put(
    "/model-sources/{source_id}",
    response_model=AccountColorsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_model_source_color(
    source_id: str,
    payload: AccountColorUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountColorsResponse:
    service = AccountColorService(session)
    if not await service.set_model_source_color(source_id, payload.chart_color):
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return await _colors(service)
