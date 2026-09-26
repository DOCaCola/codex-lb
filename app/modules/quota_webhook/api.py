from fastapi import APIRouter, Depends, Request, Response

from app.core.audit.service import AuditActor, AuditService
from app.core.auth.dashboard_access import DashboardPrincipal, Permission
from app.core.auth.dependencies import (
    require_dashboard_permission,
    require_dashboard_write_access,
    set_dashboard_error_format,
    validate_dashboard_session,
)
from app.core.exceptions import DashboardBadRequestError
from app.dependencies import get_quota_webhook_service
from app.modules.quota_webhook.schemas import QueuedTest, SavedDestination, WebhookStatus, WebhookUpdate
from app.modules.quota_webhook.service import QuotaWebhookService

router = APIRouter(
    prefix="/api/settings/quota-reset-webhook",
    tags=["dashboard"],
    dependencies=[
        Depends(validate_dashboard_session),
        Depends(set_dashboard_error_format),
    ],
)


@router.get("", response_model=WebhookStatus)
async def status(service: QuotaWebhookService = Depends(get_quota_webhook_service)) -> WebhookStatus:
    return await service.status()


@router.get("/destination", response_model=SavedDestination)
async def saved_destination(
    response: Response,
    principal: DashboardPrincipal = Depends(require_dashboard_permission(Permission.SECURITY_WRITE)),
    service: QuotaWebhookService = Depends(get_quota_webhook_service),
) -> SavedDestination:
    response.headers["Cache-Control"] = "no-store"
    url = await service.saved_destination()
    AuditService.log_async("quota_webhook_destination_revealed", actor=AuditActor.from_principal(principal))
    return SavedDestination(url=url)


@router.put(
    "", response_model=WebhookStatus, dependencies=[Depends(require_dashboard_permission(Permission.SECURITY_WRITE))]
)
async def update(
    payload: WebhookUpdate,
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: QuotaWebhookService = Depends(get_quota_webhook_service),
) -> WebhookStatus:
    try:
        result = await service.update(payload)
    except ValueError as exc:
        raise DashboardBadRequestError(str(exc), code="invalid_webhook") from exc
    AuditService.log_async(
        "quota_webhook_configured", actor=AuditActor.from_principal(principal), details={"enabled": result.enabled}
    )
    return result


@router.post(
    "/test", response_model=QueuedTest, dependencies=[Depends(require_dashboard_permission(Permission.SECURITY_WRITE))]
)
async def test(
    request: Request,
    principal: DashboardPrincipal = Depends(require_dashboard_write_access),
    service: QuotaWebhookService = Depends(get_quota_webhook_service),
) -> QueuedTest:
    try:
        result = await service.test()
    except ValueError as exc:
        raise DashboardBadRequestError(str(exc), code="invalid_webhook") from exc
    AuditService.log_async(
        "quota_webhook_test_queued", actor=AuditActor.from_principal(principal), details={"event_id": result.event_id}
    )
    return result
