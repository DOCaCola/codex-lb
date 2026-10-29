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
from app.dependencies import get_antigravity_service
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.schemas import (
    AntigravityAccountResponse,
    AntigravityAccountsResponse,
    AntigravityImport,
    AntigravityReconnect,
    AntigravityUpdate,
    OAuthComplete,
    OAuthStart,
    OAuthStarted,
)
from app.modules.antigravity.service import AntigravityService
from app.modules.antigravity.version import AntigravityVersionService, VersionStatus, VersionUpdate
from app.modules.model_sources.service import ModelSourceNotFoundError
from app.modules.model_sources.trends import ProviderTrends, read_antigravity_trends

router = APIRouter(
    prefix="/api/antigravity-accounts",
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


def _bad_request(exc: AntigravityError) -> DashboardBadRequestError:
    return DashboardBadRequestError(str(exc), code=exc.code)


@router.get("", response_model=AntigravityAccountsResponse)
async def list_accounts(
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountsResponse:
    return AntigravityAccountsResponse(accounts=await service.list_accounts())


@router.post("/import", response_model=AntigravityAccountResponse)
async def import_account(
    payload: AntigravityImport,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountResponse:
    try:
        result = await service.import_account(payload)
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_account_imported", result.id)
    return result


@router.post("/oauth/start", response_model=OAuthStarted)
async def start_oauth(
    payload: OAuthStart,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> OAuthStarted:
    try:
        result = await service.start_oauth(payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_oauth_started", payload.source_id or "new")
    return result


@router.post("/oauth/complete", response_model=AntigravityAccountResponse)
async def complete_oauth(
    payload: OAuthComplete,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountResponse:
    try:
        result = await service.complete_oauth(payload)
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_oauth_completed", result.id)
    return result


@router.get("/version", response_model=VersionStatus)
async def version_status(service: AntigravityService = Depends(get_antigravity_service)) -> VersionStatus:
    return await AntigravityVersionService(service.repository.session).status()


@router.patch("/version", response_model=VersionStatus)
async def update_version(
    payload: VersionUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> VersionStatus:
    try:
        result = await AntigravityVersionService(service.repository.session).update(payload)
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_version_updated", "version")
    return result


@router.get("/{source_id}/trends", response_model=ProviderTrends)
async def account_trends(
    source_id: str, service: AntigravityService = Depends(get_antigravity_service)
) -> ProviderTrends:
    if await service.repository.get(source_id) is None:
        raise DashboardNotFoundError("Antigravity account not found")
    return await read_antigravity_trends(service.repository.session, source_id)


@router.patch("/{source_id}", response_model=AntigravityAccountResponse)
async def update_account(
    source_id: str,
    payload: AntigravityUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountResponse:
    try:
        result = await service.update(source_id, payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_account_updated", source_id)
    return result


@router.post("/{source_id}/refresh", response_model=AntigravityAccountResponse)
async def refresh_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountResponse:
    try:
        result = await service.refresh(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_account_refreshed", source_id)
    return result


@router.post("/{source_id}/reconnect", response_model=AntigravityAccountResponse)
async def reconnect_account(
    source_id: str,
    payload: AntigravityReconnect,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> AntigravityAccountResponse:
    try:
        result = await service.reconnect(source_id, payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except AntigravityError as exc:
        raise _bad_request(exc) from exc
    _audit(request, principal, "antigravity_account_reconnected", source_id)
    return result


@router.delete("/{source_id}", status_code=204)
async def delete_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: AntigravityService = Depends(get_antigravity_service),
) -> Response:
    try:
        await service.delete(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    _audit(request, principal, "antigravity_account_deleted", source_id)
    return Response(status_code=204)
