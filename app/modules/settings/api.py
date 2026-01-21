from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from app.dependencies import SettingsContext, get_settings_context
from app.modules.settings.schemas import DashboardSettingsResponse, DashboardSettingsUpdateRequest
from app.modules.settings.service import DashboardSettingsData

router = APIRouter(prefix="/api/settings", tags=["dashboard"])


@router.get("", response_model=DashboardSettingsResponse)
async def get_settings(
    context: SettingsContext = Depends(get_settings_context),
) -> DashboardSettingsResponse:
    settings = await context.service.get_settings()
    return DashboardSettingsResponse(
        sticky_threads_enabled=settings.sticky_threads_enabled,
        prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
    )


@router.put("", response_model=DashboardSettingsResponse)
async def update_settings(
    payload: DashboardSettingsUpdateRequest = Body(...),
    context: SettingsContext = Depends(get_settings_context),
) -> DashboardSettingsResponse:
    updated = await context.service.update_settings(
        DashboardSettingsData(
            sticky_threads_enabled=payload.sticky_threads_enabled,
            prefer_earlier_reset_accounts=payload.prefer_earlier_reset_accounts,
        )
    )
    return DashboardSettingsResponse(
        sticky_threads_enabled=updated.sticky_threads_enabled,
        prefer_earlier_reset_accounts=updated.prefer_earlier_reset_accounts,
    )
