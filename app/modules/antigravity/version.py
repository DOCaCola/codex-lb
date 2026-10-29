"""Native CLI identity following: version and build changelist as one verified record.

The manifest carries version, archive URL and SHA-512 but not the changelist the
User-Agent needs. The changelist is stamped into the CLI binary
("changelist <n> with baseline <n>") and is a property of the build, not the
version: a rebuilt archive may keep its version string. A new build is therefore
downloaded, checksum-verified and scanned before it is used, and a version is never
sent without the changelist of the same build.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.http import lease_model_source_session
from app.core.utils.time import utcnow
from app.db.models import AntigravityClientBuild, AntigravityVersionState
from app.modules.antigravity.constants import DEFAULT_PLATFORM, MANIFEST_URL, PLATFORMS
from app.modules.antigravity.errors import AntigravityError
from app.modules.shared.schemas import DashboardModel

logger = logging.getLogger(__name__)

CHECK_INTERVAL = timedelta(hours=24)
RETRY_INTERVAL = timedelta(minutes=30)
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
VERSION_PATTERN = re.compile(r"^[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}$")
STAMP_PATTERN = re.compile(rb"changelist ([0-9]{6,12}) with baseline [0-9]{6,12}")
ARCHIVE_HOST = "storage.googleapis.com"


class Manifest(BaseModel):
    version: str
    url: str
    sha512: str = Field(pattern=r"^[0-9a-f]{128}$")


@dataclass(frozen=True)
class ClientIdentity:
    version: str
    changelist: str
    platform: str

    @property
    def user_agent(self) -> str:
        os_type, arch = self.platform.split("_", 1)
        return (
            f"antigravity/cli/{self.version} "
            f"(aidev_client; os_type={os_type}; arch={arch}; cl={self.changelist}; auth_method=consumer)"
        )


class BuildView(DashboardModel):
    sha512: str
    version: str
    changelist: str
    build_id: str | None
    verified_at: datetime


class VersionStatus(DashboardModel):
    platform: str
    platforms: list[str]
    effective: BuildView | None
    pinned_sha512: str | None
    builds: list[BuildView]
    last_checked_at: datetime | None
    retry_at: datetime | None
    error: str | None


class VersionUpdate(DashboardModel):
    platform: str | None = None
    pinned_sha512: str | None = None
    clear_pin: bool = False


def build_id_from_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if "antigravity-cli" in parts and parts.index("antigravity-cli") + 1 < len(parts):
        return parts[parts.index("antigravity-cli") + 1]
    return None


def extract_changelist(archive_path: str) -> str:
    """Scan every regular file in the archive for the build stamp; all stamps must agree."""
    found: set[str] = set()
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            tail = b""
            while chunk := handle.read(1024 * 1024):
                window = tail + chunk
                found.update(match.group(1).decode() for match in STAMP_PATTERN.finditer(window))
                tail = window[-96:]
    if len(found) != 1:
        raise AntigravityError(
            "CLI archive has no build changelist stamp" if not found else "CLI archive has conflicting changelists"
        )
    return found.pop()


class AntigravityVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _state(self) -> AntigravityVersionState:
        row = await self.session.get(AntigravityVersionState, 1, populate_existing=True)
        if row is not None:
            return row
        if self.session.get_bind().dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await self.session.execute(
            insert(AntigravityVersionState).values(id=1, platform=DEFAULT_PLATFORM).on_conflict_do_nothing()
        )
        await self.session.commit()
        row = await self.session.get(AntigravityVersionState, 1, populate_existing=True)
        assert row is not None
        return row

    async def _builds(self, platform: str) -> list[AntigravityClientBuild]:
        rows = await self.session.scalars(
            select(AntigravityClientBuild)
            .where(AntigravityClientBuild.platform == platform)
            .order_by(AntigravityClientBuild.verified_at.desc())
        )
        return list(rows)

    async def _effective(self, state: AntigravityVersionState) -> AntigravityClientBuild | None:
        for sha in (state.pinned_sha512, state.current_sha512):
            if sha is not None:
                build = await self.session.get(AntigravityClientBuild, sha)
                if build is not None and build.platform == state.platform:
                    return build
        builds = await self._builds(state.platform)
        return builds[0] if builds else None

    async def snapshot(self) -> ClientIdentity:
        state = await self._state()
        build = await self._effective(state)
        if build is None:
            raise AntigravityError(
                f"No verified Antigravity CLI build exists for platform {state.platform}; wait for the version check",
                code="antigravity_identity_unavailable",
                status_code=503,
            )
        return ClientIdentity(build.version, build.changelist, state.platform)

    async def status(self) -> VersionStatus:
        state = await self._state()
        effective = await self._effective(state)
        return VersionStatus(
            platform=state.platform,
            platforms=list(PLATFORMS),
            effective=_view(effective) if effective else None,
            pinned_sha512=state.pinned_sha512,
            builds=[_view(build) for build in await self._builds(state.platform)],
            last_checked_at=state.last_checked_at,
            retry_at=state.retry_at,
            error=state.error,
        )

    async def update(self, payload: VersionUpdate) -> VersionStatus:
        state = await self._state()
        values: dict[str, object] = {}
        platform = state.platform
        if payload.platform is not None and payload.platform != state.platform:
            if payload.platform not in PLATFORMS:
                raise AntigravityError("Unknown Antigravity CLI platform")
            platform = payload.platform
            # Builds are per platform; a pin or current build of another platform cannot apply.
            values.update(platform=platform, current_sha512=None, pinned_sha512=None, last_checked_at=None)
        if payload.clear_pin:
            values["pinned_sha512"] = None
        elif payload.pinned_sha512 is not None:
            build = await self.session.get(AntigravityClientBuild, payload.pinned_sha512)
            if build is None or build.platform != platform:
                raise AntigravityError("Pin a verified build of the configured platform")
            values["pinned_sha512"] = build.sha512
        if values:
            await self.session.execute(
                update(AntigravityVersionState).where(AntigravityVersionState.id == 1).values(**values)
            )
            await self.session.commit()
        return await self.status()

    async def refresh(self, *, now: datetime | None = None, force: bool = False) -> None:
        now = now or utcnow()
        state = await self._state()
        if not force:
            if state.retry_at is not None and state.retry_at > now:
                return
            if state.last_checked_at is not None and now - state.last_checked_at < CHECK_INTERVAL:
                return
        platform = state.platform
        try:
            manifest = await _fetch_manifest(platform)
            if not VERSION_PATTERN.fullmatch(manifest.version):
                raise AntigravityError("CLI manifest returned an invalid version")
            build = await self.session.get(AntigravityClientBuild, manifest.sha512)
            if build is None:
                changelist = await _verified_changelist(manifest)
                build = AntigravityClientBuild(
                    sha512=manifest.sha512,
                    platform=platform,
                    version=manifest.version,
                    changelist=changelist,
                    build_id=build_id_from_url(manifest.url),
                    archive_url=manifest.url,
                    verified_at=utcnow(),
                )
                self.session.add(build)
                await self.session.flush()
                logger.info(
                    "antigravity_client_build_verified platform=%s version=%s changelist=%s",
                    platform,
                    build.version,
                    build.changelist,
                )
            elif build.platform != platform:
                raise AntigravityError("CLI manifest archive belongs to another platform")
            # A concurrent platform change wins: only this platform's state is updated.
            await self.session.execute(
                update(AntigravityVersionState)
                .where(AntigravityVersionState.id == 1, AntigravityVersionState.platform == platform)
                .values(current_sha512=build.sha512, last_checked_at=now, retry_at=None, error=None)
            )
        except (aiohttp.ClientError, TimeoutError, ValueError, OSError, tarfile.TarError) as exc:
            await self.session.rollback()
            message = (
                str(exc) if isinstance(exc, AntigravityError) else f"CLI version check failed: {type(exc).__name__}"
            )
            logger.warning("antigravity_version_check_failed platform=%s error=%s", platform, message)
            await self.session.execute(
                update(AntigravityVersionState)
                .where(AntigravityVersionState.id == 1)
                .values(error=message + "; keeping the last verified build", retry_at=now + RETRY_INTERVAL)
            )
        await self.session.commit()


def _view(build: AntigravityClientBuild) -> BuildView:
    return BuildView(
        sha512=build.sha512,
        version=build.version,
        changelist=build.changelist,
        build_id=build.build_id,
        verified_at=build.verified_at,
    )


async def _fetch_manifest(platform: str) -> Manifest:
    async with lease_model_source_session() as session:
        async with session.get(
            MANIFEST_URL.format(platform=platform), timeout=aiohttp.ClientTimeout(total=15), allow_redirects=False
        ) as response:
            if response.status != 200:
                raise AntigravityError(f"CLI manifest returned HTTP {response.status}")
            body = await response.content.read(64 * 1024 + 1)
            if len(body) > 64 * 1024:
                raise AntigravityError("CLI manifest exceeded its size limit")
            return Manifest.model_validate_json(body)


async def _verified_changelist(manifest: Manifest) -> str:
    parsed = urlparse(manifest.url)
    if parsed.scheme != "https" or parsed.hostname != ARCHIVE_HOST:
        raise AntigravityError("CLI manifest archive URL is not on the public release host")
    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as archive:
        digest = hashlib.sha512()
        size = 0
        async with lease_model_source_session() as session:
            async with session.get(
                manifest.url, timeout=aiohttp.ClientTimeout(total=600, sock_read=60), allow_redirects=False
            ) as response:
                if response.status != 200:
                    raise AntigravityError(f"CLI archive returned HTTP {response.status}")
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES:
                        raise AntigravityError("CLI archive exceeded its size limit")
                    digest.update(chunk)
                    archive.write(chunk)
        archive.flush()
        if digest.hexdigest() != manifest.sha512:
            raise AntigravityError("CLI archive SHA-512 does not match the manifest")
        return await asyncio.to_thread(extract_changelist, archive.name)
