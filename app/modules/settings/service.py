from __future__ import annotations

from dataclasses import dataclass

from app.modules.settings.repository import SettingsRepository


@dataclass(frozen=True, slots=True)
class DashboardSettingsData:
    sticky_threads_enabled: bool
    prefer_earlier_reset_accounts: bool


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def get_settings(self) -> DashboardSettingsData:
        row = await self._repository.get_or_create()
        return DashboardSettingsData(
            sticky_threads_enabled=row.sticky_threads_enabled,
            prefer_earlier_reset_accounts=row.prefer_earlier_reset_accounts,
        )

    async def update_settings(self, payload: DashboardSettingsData) -> DashboardSettingsData:
        row = await self._repository.update(
            sticky_threads_enabled=payload.sticky_threads_enabled,
            prefer_earlier_reset_accounts=payload.prefer_earlier_reset_accounts,
        )
        return DashboardSettingsData(
            sticky_threads_enabled=row.sticky_threads_enabled,
            prefer_earlier_reset_accounts=row.prefer_earlier_reset_accounts,
        )
