"""Claude Code identity following: CLI, SDK and runtime versions as one verified release.

Claude Code reports its Stainless SDK version and the Node-compatible version of its
embedded Bun runtime next to its CLI version. Both are fixed when the release is built,
so advertising a newer CLI version with older SDK/runtime values describes a client that
never existed (sub2api #8440). A new stable release is therefore adopted only after its
published native build was downloaded, checked against the registry's integrity hash and
scanned for both values. The build is never executed.

Anthropic gates new models on a minimum Claude Code version (claude_code_version_too_old,
sub2api #6481/#7532), so releases keep being followed rather than pinned to a reviewed list.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
import tarfile
import tempfile
from datetime import datetime, timedelta
from typing import IO
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.http import lease_model_source_session
from app.core.utils.time import utcnow
from app.db.models import ClaudeClientBuild, ClaudeVersionState
from app.modules.claude.client import bounded_body
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import ClientBuild
from app.modules.shared.schemas import DashboardModel

logger = logging.getLogger(__name__)

# Builds verified when this code was reviewed, by scanning their published native builds.
REVIEWED_BUILDS = {
    build.version: build
    for build in (
        ClientBuild("2.1.282", "0.112.1", "v26.3.0"),
        ClientBuild("2.1.316", "0.128.0", "v26.12.1"),
    )
}
BASELINE_VERSION = "2.1.316"
RELEASE_URL = "https://api.github.com/repos/anthropics/claude-code/releases/latest"
# The SDK and runtime versions are build-time constants shared by every platform package of a release.
PACKAGE = "@anthropic-ai/claude-code-linux-x64"
PACKAGE_URL = "https://registry.npmjs.org/@anthropic-ai%2fclaude-code-linux-x64/{version}"
PACKAGE_HOST = "registry.npmjs.org"
BINARY_MEMBER = "package/claude"
MAX_PACKAGE_BYTES = 512 * 1024 * 1024
RETRY_INTERVAL = timedelta(minutes=15)
VERSION_PATTERN = re.compile(r"^[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}$")
# Every request-header reference names the SDK's version binding; the binding holds the version.
SDK_REFERENCE = re.compile(rb'"X-Stainless-Package-Version":([A-Za-z_$][A-Za-z0-9_$]{0,63})')
SEMVER_BINDING = re.compile(
    rb'(?:var|let|const) ([A-Za-z_$][A-Za-z0-9_$]{0,63})="([0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5})"'
)
# Bun's npm user-agent template carries the Node version that process.version reports.
RUNTIME_STAMP = re.compile(rb"bun/[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5} npm/\? node/(v[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5})")
# Longer than any match, so a match starting before the scanned limit lies wholly inside the window.
_OVERLAP = 256
_CHUNK = 4 * 1024 * 1024


def validate_version(value: str) -> str:
    if not VERSION_PATTERN.fullmatch(value):
        raise ClaudeError("Claude version must be a stable major.minor.patch version")
    return value


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(map(int, version.split(".")))


class Release(BaseModel):
    tag_name: str
    draft: bool
    prerelease: bool


class PackageDist(BaseModel):
    tarball: str
    integrity: str = Field(pattern=r"^sha512-[A-Za-z0-9+/]{86}==$")


class PackageVersion(BaseModel):
    version: str
    dist: PackageDist


class BuildView(DashboardModel):
    version: str
    sdk_version: str
    runtime_version: str
    # None for builds verified when the code was reviewed.
    verified_at: datetime | None


class VersionStatus(DashboardModel):
    effective: BuildView
    discovered_version: str
    pinned_version: str | None
    builds: list[BuildView]
    last_checked_at: datetime | None
    last_changed_at: datetime | None
    retry_at: datetime | None
    error: str | None


class VersionPin(DashboardModel):
    version: str | None


def extract_runtime_identity(package_path: str) -> tuple[str, str]:
    """The SDK and runtime versions stamped into the package's native binary."""
    with tarfile.open(package_path, mode="r|gz") as package:
        for member in package:
            if member.name == BINARY_MEMBER and member.isfile():
                handle = package.extractfile(member)
                if handle is None:
                    raise ClaudeError("Claude Code package binary is unreadable")
                return _scan_binary(handle)
    raise ClaudeError("Claude Code package has no native binary")


def _scan_binary(handle: IO[bytes]) -> tuple[str, str]:
    references: set[bytes] = set()
    bindings: dict[bytes, set[bytes]] = {}
    runtimes: set[bytes] = set()
    window = b""
    while True:
        chunk = handle.read(_CHUNK)
        window += chunk
        limit = len(window) if not chunk else max(len(window) - _OVERLAP, 0)
        for match in SDK_REFERENCE.finditer(window):
            if match.start() < limit:
                references.add(match.group(1))
        for match in SEMVER_BINDING.finditer(window):
            if match.start() < limit:
                bindings.setdefault(match.group(1), set()).add(match.group(2))
        for match in RUNTIME_STAMP.finditer(window):
            if match.start() < limit:
                runtimes.add(match.group(1))
        if not chunk:
            break
        window = window[limit:]
    if len(references) != 1:
        raise ClaudeError("Claude Code binary has no unambiguous SDK version reference")
    versions = bindings.get(references.pop(), set())
    if len(versions) != 1 or len(runtimes) != 1:
        raise ClaudeError("Claude Code binary has no unambiguous SDK and runtime version")
    return versions.pop().decode(), runtimes.pop().decode()


class ClaudeVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _build(self, version: str) -> ClientBuild | None:
        if version in REVIEWED_BUILDS:
            return REVIEWED_BUILDS[version]
        row = await self.session.get(ClaudeClientBuild, version)
        return ClientBuild(row.version, row.sdk_version, row.runtime_version) if row else None

    async def snapshot(self) -> ClientBuild:
        row = await self.session.get(ClaudeVersionState, 1, populate_existing=True)
        version = (row.pinned_version or row.discovered_version) if row else BASELINE_VERSION
        build = await self._build(version)
        if build is None:
            raise ClaudeError(f"Claude Code {version} has no verified build")
        return build

    async def status(self) -> VersionStatus:
        row = await self.session.get(ClaudeVersionState, 1, populate_existing=True)
        views = [BuildView(**vars(build), verified_at=None) for build in REVIEWED_BUILDS.values()]
        views += [
            BuildView(
                version=build.version,
                sdk_version=build.sdk_version,
                runtime_version=build.runtime_version,
                verified_at=build.verified_at,
            )
            for build in await self.session.scalars(select(ClaudeClientBuild))
        ]
        views.sort(key=lambda view: _version_key(view.version), reverse=True)
        effective = (await self.snapshot()).version
        return VersionStatus(
            effective=next(view for view in views if view.version == effective),
            discovered_version=row.discovered_version if row else BASELINE_VERSION,
            pinned_version=row.pinned_version if row else None,
            builds=views,
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

    async def pin(self, version: str | None) -> ClientBuild:
        if version is not None and await self._build(validate_version(version)) is None:
            raise ClaudeError("Pin a verified Claude Code build")
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
            newer = _version_key(version) > _version_key(row.discovered_version)
            if newer and await self._build(version) is None:
                await self._verify(version)
            # Only update discovery fields, so a concurrent operator pin cannot
            # be overwritten by a slow release verification.
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
        except (aiohttp.ClientError, TimeoutError, ValueError, OSError, tarfile.TarError) as exc:
            # The ETag is kept only with a verified result, so the release is checked again.
            await self.session.rollback()
            message = str(exc) if isinstance(exc, ClaudeError) else f"Release check failed: {type(exc).__name__}"
            logger.warning("claude_version_check_failed error=%s", message)
            await self.session.execute(
                update(ClaudeVersionState)
                .where(ClaudeVersionState.id == 1)
                .values(error=message + "; keeping the last verified version", retry_at=now + RETRY_INTERVAL)
            )
        await self.session.commit()

    async def _verify(self, version: str) -> None:
        dist = await _package_dist(version)
        sdk_version, runtime_version = await _verified_runtime_identity(dist)
        self.session.add(
            ClaudeClientBuild(
                version=version,
                sdk_version=sdk_version,
                runtime_version=runtime_version,
                package=PACKAGE,
                integrity=dist.integrity,
                verified_at=utcnow(),
            )
        )
        await self.session.flush()
        logger.info(
            "claude_client_build_verified version=%s sdk_version=%s runtime_version=%s",
            version,
            sdk_version,
            runtime_version,
        )


async def _package_dist(version: str) -> PackageDist:
    async with lease_model_source_session() as session:
        async with session.get(
            PACKAGE_URL.format(version=version), timeout=aiohttp.ClientTimeout(total=15), allow_redirects=False
        ) as response:
            if response.status != 200:
                raise ClaudeError(f"Claude Code package metadata returned HTTP {response.status}")
            package = PackageVersion.model_validate_json(await bounded_body(response))
    tarball = urlparse(package.dist.tarball)
    if package.version != version or tarball.scheme != "https" or tarball.hostname != PACKAGE_HOST:
        raise ClaudeError("Claude Code package metadata does not describe this release")
    return package.dist


async def _verified_runtime_identity(dist: PackageDist) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(suffix=".tgz") as package:
        digest = hashlib.sha512()
        size = 0
        async with lease_model_source_session() as session:
            async with session.get(
                dist.tarball, timeout=aiohttp.ClientTimeout(total=600, sock_read=60), allow_redirects=False
            ) as response:
                if response.status != 200:
                    raise ClaudeError(f"Claude Code package returned HTTP {response.status}")
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_PACKAGE_BYTES:
                        raise ClaudeError("Claude Code package exceeded its size limit")
                    digest.update(chunk)
                    package.write(chunk)
        package.flush()
        if "sha512-" + base64.b64encode(digest.digest()).decode() != dist.integrity:
            raise ClaudeError("Claude Code package does not match its registry integrity hash")
        return await asyncio.to_thread(extract_runtime_identity, package.name)
