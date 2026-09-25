from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.http import lease_model_source_session
from app.core.utils.time import utcnow
from app.db.models import ClaudeVersionState
from app.modules.claude.client import bounded_body
from app.modules.claude.credentials import ClaudeError
from app.modules.shared.schemas import DashboardModel

BASELINE_VERSION = "2.1.282"
RELEASE_URL = "https://api.github.com/repos/anthropics/claude-code/releases/latest"
VERSION_PATTERN = re.compile(r"^[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}$")


def validate_version(value: str) -> str:
    if not VERSION_PATTERN.fullmatch(value):
        raise ClaudeError("Claude version must be a stable major.minor.patch version")
    return value


class Release(BaseModel):
    tag_name: str
    draft: bool
    prerelease: bool


@dataclass(frozen=True)
class IdentitySnapshot:
    version: str


class VersionStatus(DashboardModel):
    effective_version: str
    discovered_version: str
    pinned_version: str | None
    last_checked_at: datetime | None
    last_changed_at: datetime | None
    retry_at: datetime | None
    error: str | None


class VersionPin(DashboardModel):
    version: str | None


class ClaudeVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self) -> IdentitySnapshot:
        row = await self.session.get(ClaudeVersionState, 1, populate_existing=True)
        return IdentitySnapshot(row.pinned_version or row.discovered_version if row else BASELINE_VERSION)

    async def status(self) -> VersionStatus:
        row = await self.session.get(ClaudeVersionState, 1, populate_existing=True)
        return VersionStatus(
            effective_version=(row.pinned_version or row.discovered_version) if row else BASELINE_VERSION,
            discovered_version=row.discovered_version if row else BASELINE_VERSION,
            pinned_version=row.pinned_version if row else None,
            last_checked_at=row.last_checked_at if row else None,
            last_changed_at=row.last_changed_at if row else None,
            retry_at=row.retry_at if row else None,
            error=row.error if row else None,
        )

    async def _ensure(self) -> ClaudeVersionState:
        if self.session.get_bind().dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await self.session.execute(
            insert(ClaudeVersionState).values(id=1, discovered_version=BASELINE_VERSION).on_conflict_do_nothing()
        )
        await self.session.commit()
        row = await self.session.get(ClaudeVersionState, 1, populate_existing=True)
        assert row is not None
        return row

    async def pin(self, version: str | None) -> IdentitySnapshot:
        if version is not None:
            validate_version(version)
        await self._ensure()
        await self.session.execute(
            update(ClaudeVersionState).where(ClaudeVersionState.id == 1).values(pinned_version=version)
        )
        await self.session.commit()
        return await self.snapshot()

    async def refresh(self, *, now: datetime | None = None) -> None:
        now = now or utcnow()
        row = await self._ensure()
        if row.retry_at is not None and row.retry_at > now:
            return
        if row.last_checked_at is not None and now - row.last_checked_at < timedelta(hours=24):
            return
        headers = {"Accept": "application/vnd.github+json"}
        if row.etag:
            headers["If-None-Match"] = row.etag
        try:
            async with lease_model_source_session() as session:
                async with session.get(
                    RELEASE_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False
                ) as response:
                    if response.status == 304:
                        version = row.discovered_version
                    elif response.status == 200:
                        release = Release.model_validate_json(await bounded_body(response))
                        if release.draft or release.prerelease:
                            raise ClaudeError("Claude release feed did not return a stable release")
                        version = validate_version(release.tag_name.removeprefix("v"))
                    else:
                        raise ClaudeError(f"Claude release feed returned HTTP {response.status}")
                    etag = response.headers.get("ETag", row.etag)
            newer = tuple(map(int, version.split("."))) > tuple(map(int, row.discovered_version.split(".")))
            # Only update discovery fields, so a concurrent operator pin cannot
            # be overwritten by a slow metadata fetch.
            await self.session.execute(
                update(ClaudeVersionState)
                .where(ClaudeVersionState.id == 1)
                .values(
                    discovered_version=version if newer else row.discovered_version,
                    last_checked_at=now,
                    last_changed_at=now if newer else row.last_changed_at,
                    retry_at=None,
                    error=None,
                    etag=etag,
                )
            )
        except (aiohttp.ClientError, TimeoutError, ValueError):
            await self.session.execute(
                update(ClaudeVersionState)
                .where(ClaudeVersionState.id == 1)
                .values(
                    error="Stable release discovery failed; retaining the last known version",
                    retry_at=now + timedelta(minutes=15),
                )
            )
        await self.session.commit()
