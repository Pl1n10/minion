"""Filesystem-only backend. Always available, no external deps."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from .base import BackendStatus, FileEntry, RepoBackend

LANG_EXT: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".psd1": "powershell",
    ".sql": "sql",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".tf": "terraform",
}


def _matches_any(rel: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
        # also match the pattern against any path segment for "**" prefixes
        if pat.endswith("/**") and rel.startswith(pat[:-3] + "/"):
            return True
    return False


class FilesystemBackend(RepoBackend):
    name = "filesystem"

    def __init__(self, root: Path, ignore_globs: list[str] | None = None) -> None:
        self.root = root
        self.ignore_globs = ignore_globs or []

    def status(self) -> BackendStatus:
        return BackendStatus(
            name=self.name,
            available=self.root.exists(),
            detail=f"scanning {self.root}",
        )

    def list_files(self) -> list[FileEntry]:
        out: list[FileEntry] = []
        root = self.root
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if _matches_any(rel, self.ignore_globs):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            out.append(
                FileEntry(
                    path=Path(rel),
                    size=size,
                    language=LANG_EXT.get(path.suffix.lower()),
                )
            )
        out.sort(key=lambda f: f.relpath)
        return out
