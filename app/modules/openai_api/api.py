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
from app.dependencies import get_openai_api_service
from app.modules.model_sources.service import ModelSourceNotFoundError
from app.modules.model_sources.trends import ProviderTrends, read_trends
from app.modules.openai_api.client import OpenAIApiError
from app.modules.openai_api.schemas import (
    OpenAIApiAccountResponse,
    OpenAIApiAccountsResponse,
    OpenAIApiCreate,
    OpenAIApiUpdate,
)
from app.modules.openai_api.service import OpenAIApiService

router = APIRouter(
    prefix="/api/openai-api-accounts",
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


@router.get("", response_model=OpenAIApiAccountsResponse)
async def list_accounts(service: OpenAIApiService = Depends(get_openai_api_service)) -> OpenAIApiAccountsResponse:
    return OpenAIApiAccountsResponse(accounts=await service.list_accounts())


@router.post("", response_model=OpenAIApiAccountResponse)
async def create_account(
    payload: OpenAIApiCreate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenAIApiService = Depends(get_openai_api_service),
) -> OpenAIApiAccountResponse:
    try:
        result = await service.create(payload)
    except OpenAIApiError as exc:
        raise DashboardBadRequestError(str(exc), code="openai_api_error") from exc
    _audit(request, principal, "openai_api_account_created", result.id)
    return result


@router.get("/{source_id}/trends", response_model=ProviderTrends)
async def account_trends(source_id: str, service: OpenAIApiService = Depends(get_openai_api_service)) -> ProviderTrends:
    if await service.repository.get(source_id) is None:
        raise DashboardNotFoundError("OpenAI API account not found")
    return await read_trends(service.repository.session, source_id, quota=False)


@router.patch("/{source_id}", response_model=OpenAIApiAccountResponse)
async def update_account(
    source_id: str,
    payload: OpenAIApiUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenAIApiService = Depends(get_openai_api_service),
) -> OpenAIApiAccountResponse:
    try:
        result = await service.update(source_id, payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except OpenAIApiError as exc:
        raise DashboardBadRequestError(str(exc), code="openai_api_error") from exc
    _audit(request, principal, "openai_api_account_updated", source_id)
    return result


@router.post("/{source_id}/refresh", response_model=OpenAIApiAccountResponse)
async def refresh_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenAIApiService = Depends(get_openai_api_service),
) -> OpenAIApiAccountResponse:
    try:
        result = await service.refresh(source_id, operator=True)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except OpenAIApiError as exc:
        raise DashboardBadRequestError(str(exc), code="openai_api_error") from exc
    _audit(request, principal, "openai_api_account_refreshed", source_id)
    return result


@router.delete("/{source_id}", status_code=204)
async def delete_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: OpenAIApiService = Depends(get_openai_api_service),
) -> Response:
    try:
        await service.delete(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    _audit(request, principal, "openai_api_account_deleted", source_id)
    return Response(status_code=204)
