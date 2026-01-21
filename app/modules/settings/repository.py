from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DashboardSettings

_SETTINGS_ID = 1


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> DashboardSettings:
        existing = await self._session.get(DashboardSettings, _SETTINGS_ID)
        if existing is not None:
            return existing

        row = DashboardSettings(
            id=_SETTINGS_ID,
            sticky_threads_enabled=False,
            prefer_earlier_reset_accounts=False,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def update(
        self,
        *,
        sticky_threads_enabled: bool,
        prefer_earlier_reset_accounts: bool,
    ) -> DashboardSettings:
        settings = await self.get_or_create()
        settings.sticky_threads_enabled = sticky_threads_enabled
        settings.prefer_earlier_reset_accounts = prefer_earlier_reset_accounts
        await self._session.commit()
        await self._session.refresh(settings)
        return settings
