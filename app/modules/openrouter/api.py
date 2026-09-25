from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.core.audit.service import AuditActor, AuditService, AuditTarget
from app.core.auth.dashboard_access import DashboardPrincipal
from app.core.auth.dependencies import (
    require_dashboard_write_access,
    set_dashboard_error_format,
    validate_dashboard_session,
)
from app.core.exceptions import DashboardBadRequestError, DashboardNotFoundError
from app.dependencies import get_openrouter_service
from app.modules.model_sources.service import ModelSourceNotFoundError
from app.modules.openrouter.client import OpenRouterError
from app.modules.openrouter.schemas import (
    OpenRouterAccountResponse,
    OpenRouterAccountsResponse,
    OpenRouterCreate,
    OpenRouterUpdate,
)
from app.modules.openrouter.service import OpenRouterService

router = APIRouter(
    prefix="/api/openrouter-accounts",
    tags=["dashboard"],
    dependencies=[Depends(validate_dashboard_session), Depends(set_dashboard_error_format)],
)


def _audit(request: Request, principal: DashboardPrincipal, action: str, source_id: str) -> None:
    AuditService.log_async(
        action,
        actor_ip=request.client.host if request.client else None,
        actor=AuditActor.from_principal(principal),
        target=AuditTarget("model_source", source_id),
    )


@router.get("", response_model=OpenRouterAccountsResponse)
async def list_accounts(service: OpenRouterService = Depends(get_openrouter_service)) -> OpenRouterAccountsResponse:
    return OpenRouterAccountsResponse(accounts=await service.list_accounts())


@router.post("", response_model=OpenRouterAccountResponse)
async def create_account(
    payload: OpenRouterCreate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenRouterService = Depends(get_openrouter_service),
) -> OpenRouterAccountResponse:
    try:
        result = await service.create(payload)
    except OpenRouterError as exc:
        raise DashboardBadRequestError(str(exc), code="openrouter_error") from exc
    _audit(request, principal, "openrouter_account_created", result.id)
    return result


@router.patch("/{source_id}", response_model=OpenRouterAccountResponse)
async def update_account(
    source_id: str,
    payload: OpenRouterUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenRouterService = Depends(get_openrouter_service),
) -> OpenRouterAccountResponse:
    try:
        result = await service.update(source_id, payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except OpenRouterError as exc:
        raise DashboardBadRequestError(str(exc), code="openrouter_error") from exc
    _audit(request, principal, "openrouter_account_updated", source_id)
    return result


@router.post("/{source_id}/refresh", response_model=OpenRouterAccountResponse)
async def refresh_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenRouterService = Depends(get_openrouter_service),
) -> OpenRouterAccountResponse:
    try:
        result = await service.refresh(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except OpenRouterError as exc:
        raise DashboardBadRequestError(str(exc), code="openrouter_error") from exc
    _audit(request, principal, "openrouter_account_refreshed", source_id)
    return result


@router.delete("/{source_id}", status_code=204)
async def delete_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenRouterService = Depends(get_openrouter_service),
) -> Response:
    try:
        await service.delete(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    _audit(request, principal, "openrouter_account_deleted", source_id)
    return Response(status_code=204)
