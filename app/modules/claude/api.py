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
from app.dependencies import get_claude_service
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import (
    ClaudeAccountResponse,
    ClaudeAccountsResponse,
    ClaudeImport,
    ClaudeUpdate,
    OAuthComplete,
    OAuthStart,
    OAuthStarted,
)
from app.modules.claude.service import ClaudeService
from app.modules.claude.version import ClaudeVersionService, VersionPin, VersionStatus
from app.modules.model_sources.service import ModelSourceNotFoundError

router = APIRouter(
    prefix="/api/claude-accounts",
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


@router.get("", response_model=ClaudeAccountsResponse)
async def list_accounts(service: ClaudeService = Depends(get_claude_service)) -> ClaudeAccountsResponse:
    return ClaudeAccountsResponse(accounts=await service.list_accounts())


@router.post("/import", response_model=ClaudeAccountResponse)
async def import_account(
    payload: ClaudeImport,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> ClaudeAccountResponse:
    try:
        result = await service.import_account(payload)
    except ClaudeError as exc:
        raise DashboardBadRequestError(str(exc), code="claude_error") from exc
    _audit(request, principal, "claude_account_imported", result.id)
    return result


@router.post("/oauth/start", response_model=OAuthStarted)
async def start_oauth(
    payload: OAuthStart,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> OAuthStarted:
    result = await service.start_oauth(payload)
    _audit(request, principal, "claude_oauth_started", "new")
    return result


@router.post("/oauth/complete", response_model=ClaudeAccountResponse)
async def complete_oauth(
    payload: OAuthComplete,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> ClaudeAccountResponse:
    try:
        result = await service.complete_oauth(payload)
    except ClaudeError as exc:
        raise DashboardBadRequestError(str(exc), code="claude_error") from exc
    _audit(request, principal, "claude_account_created", result.id)
    return result


@router.get("/version", response_model=VersionStatus)
async def version_status(service: ClaudeService = Depends(get_claude_service)) -> VersionStatus:
    return await ClaudeVersionService(service.repository.session).status()


@router.patch("/version", response_model=VersionStatus)
async def pin_version(
    payload: VersionPin,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> VersionStatus:
    versions = ClaudeVersionService(service.repository.session)
    try:
        await versions.pin(payload.version)
    except ClaudeError as exc:
        raise DashboardBadRequestError(str(exc), code="claude_error") from exc
    _audit(request, principal, "claude_version_pin_updated", "version")
    return await versions.status()


@router.patch("/{source_id}", response_model=ClaudeAccountResponse)
async def update_account(
    source_id: str,
    payload: ClaudeUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> ClaudeAccountResponse:
    try:
        result = await service.update(source_id, payload)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except ClaudeError as exc:
        raise DashboardBadRequestError(str(exc), code="claude_error") from exc
    _audit(request, principal, "claude_account_updated", source_id)
    return result


@router.post("/{source_id}/refresh", response_model=ClaudeAccountResponse)
async def refresh_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> ClaudeAccountResponse:
    try:
        result = await service.refresh(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    except ClaudeError as exc:
        raise DashboardBadRequestError(str(exc), code="claude_error") from exc
    _audit(request, principal, "claude_account_refreshed", source_id)
    return result


@router.delete("/{source_id}", status_code=204)
async def delete_account(
    source_id: str,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: ClaudeService = Depends(get_claude_service),
) -> Response:
    try:
        await service.delete(source_id)
    except ModelSourceNotFoundError as exc:
        raise DashboardNotFoundError(str(exc)) from exc
    _audit(request, principal, "claude_account_deleted", source_id)
    return Response(status_code=204)
