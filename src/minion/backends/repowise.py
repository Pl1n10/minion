"""Repowise OSS backend.

MVP scope: detection only. We check whether the `repowise` CLI binary is
on PATH and surface that in status/manifest, but we do not yet rely on its
output for brief generation. A future iteration will wrap `repowise map`
or its equivalent.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import BackendStatus, FileEntry, RepoBackend
from .filesystem import FilesystemBackend


class RepowiseBackend(RepoBackend):
    name = "repowise"

    def __init__(
        self,
        root: Path,
        binary: str = "repowise",
        ignore_globs: list[str] | None = None,
    ) -> None:
        self.root = root
        self.binary = binary
        self._fallback = FilesystemBackend(root, ignore_globs=ignore_globs)

    @staticmethod
    def is_available(binary: str = "repowise") -> bool:
        return shutil.which(binary) is not None

    def _version(self) -> str | None:
        path = shutil.which(self.binary)
        if not path:
            return None
        try:
            out = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            text = (out.stdout or out.stderr).strip()
            return text or None
        except (OSError, subprocess.TimeoutExpired):
            return None

    def status(self) -> BackendStatus:
        path = shutil.which(self.binary)
        if not path:
            return BackendStatus(
                name=self.name,
                available=False,
                detail=f"`{self.binary}` not found on PATH",
            )
        return BackendStatus(
            name=self.name,
            available=True,
            detail=f"detected at {path} (using filesystem fallback for MVP)",
            version=self._version(),
        )

    def list_files(self) -> list[FileEntry]:
        # MVP: even when Repowise is detected we still source files from
        # the filesystem fallback. Hooking into `repowise map` output is a
        # follow-up.
        return self._fallback.list_files()
