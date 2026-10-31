"""Operator-set subscription end dates on provider accounts."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dashboard_access import Permission
from app.core.auth.dependencies import (
    require_dashboard_permission,
    set_dashboard_error_format,
    validate_dashboard_session,
)
from app.core.exceptions import DashboardBadRequestError, DashboardNotFoundError
from app.db.session import get_session
from app.modules.account_subscriptions.schemas import (
    AccountSubscriptionEndResponse,
    AccountSubscriptionEndsResponse,
    AccountSubscriptionEndUpdate,
)
from app.modules.account_subscriptions.service import AccountSubscriptionService

router = APIRouter(
    prefix="/api/account-subscriptions",
    tags=["dashboard"],
    dependencies=[
        Depends(validate_dashboard_session),
        Depends(set_dashboard_error_format),
    ],
)


async def _ends(service: AccountSubscriptionService) -> AccountSubscriptionEndsResponse:
    return AccountSubscriptionEndsResponse(
        ends=[
            AccountSubscriptionEndResponse(
                account_id=entry.account_id,
                model_source_id=entry.model_source_id,
                ends_at=entry.ends_at,
            )
            for entry in await service.ends()
        ]
    )


@router.get(
    "",
    response_model=AccountSubscriptionEndsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_READ))],
)
async def list_subscription_ends(session: AsyncSession = Depends(get_session)) -> AccountSubscriptionEndsResponse:
    return await _ends(AccountSubscriptionService(session))


@router.put(
    "/accounts/{account_id}",
    response_model=AccountSubscriptionEndsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_account_subscription_end(
    account_id: str,
    payload: AccountSubscriptionEndUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountSubscriptionEndsResponse:
    service = AccountSubscriptionService(session)
    if not await service.set_account_end(account_id, payload.ends_at):
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return await _ends(service)


@router.put(
    "/model-sources/{source_id}",
    response_model=AccountSubscriptionEndsResponse,
    dependencies=[Depends(require_dashboard_permission(Permission.ACCOUNTS_WRITE))],
)
async def set_model_source_subscription_end(
    source_id: str,
    payload: AccountSubscriptionEndUpdate,
    session: AsyncSession = Depends(get_session),
) -> AccountSubscriptionEndsResponse:
    service = AccountSubscriptionService(session)
    result = await service.set_model_source_end(source_id, payload.ends_at)
    if result == "not_found":
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    if result == "not_applicable":
        raise DashboardBadRequestError(
            "This account has no subscription window",
            code="subscription_end_not_applicable",
        )
    return await _ends(service)
