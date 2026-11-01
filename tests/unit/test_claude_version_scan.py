import io
import tarfile

import pytest

from app.modules.claude import version
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.version import extract_runtime_identity

pytestmark = pytest.mark.unit

# The shapes found in published Claude Code binaries (2.1.316).
HEADERS = b'{"X-Stainless-Lang":"js","X-Stainless-Package-Version":Ox,"X-Stainless-OS":r}'
BINDING = b'import{rt}from"/$bunfs/root/chunk-xvhz0qz4.js";var Ox="0.128.0";var rbi=()=>typeof window'
RUNTIME = b"fig_user_agent  *       bun/1.4.4 npm/? node/v26.12.1 darwin arm64"


def package(tmp_path, binary: bytes, *, member: str = "package/claude") -> str:
    path = tmp_path / "claude-code.tgz"
    with tarfile.open(path, "w:gz") as archive:
        for name, data in (("package/package.json", b"{}"), (member, binary)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return str(path)


def test_reads_sdk_and_runtime_versions(tmp_path, monkeypatch):
    filler = b"x" * 1000
    binary = filler + HEADERS + filler + BINDING + filler + RUNTIME + filler + HEADERS
    assert extract_runtime_identity(package(tmp_path, binary)) == ("0.128.0", "v26.12.1")
    # Matches spanning read boundaries are found whole.
    monkeypatch.setattr(version, "_CHUNK", 7)
    assert extract_runtime_identity(package(tmp_path, binary)) == ("0.128.0", "v26.12.1")


@pytest.mark.parametrize(
    "binary",
    [
        HEADERS + BINDING,
        BINDING + RUNTIME,
        HEADERS + BINDING + b'var Ox="0.112.1";' + RUNTIME,
        HEADERS + b'"X-Stainless-Package-Version":le' + BINDING + RUNTIME,
        HEADERS + BINDING + RUNTIME + b"bun/1.4.3 npm/? node/v26.3.0",
    ],
)
def test_ambiguous_or_missing_values_are_rejected(tmp_path, binary):
    with pytest.raises(ClaudeError, match="unambiguous"):
        extract_runtime_identity(package(tmp_path, binary))


def test_package_without_native_binary_is_rejected(tmp_path):
    with pytest.raises(ClaudeError, match="no native binary"):
        extract_runtime_identity(package(tmp_path, HEADERS + BINDING + RUNTIME, member="package/cli.js"))
