"""Repo-mapping backends."""

from __future__ import annotations

from pathlib import Path

from ..config import MinionConfig
from .base import BackendStatus, FileEntry, RepoBackend
from .filesystem import FilesystemBackend
from .repowise import RepowiseBackend

__all__ = [
    "BackendStatus",
    "FileEntry",
    "RepoBackend",
    "FilesystemBackend",
    "RepowiseBackend",
    "select_backend",
    "all_backend_statuses",
]


def select_backend(root: Path, cfg: MinionConfig) -> RepoBackend:
    """Pick the best available backend per config preference.

    `auto` order: repowise (if present) → filesystem.
    """
    pref = cfg.backend.preferred
    ignore = cfg.brief.ignore_globs
    if pref == "filesystem":
        return FilesystemBackend(root, ignore_globs=ignore)
    if pref == "repowise":
        return RepowiseBackend(root, binary=cfg.backend.repowise_binary, ignore_globs=ignore)
    # auto
    if RepowiseBackend.is_available(cfg.backend.repowise_binary):
        return RepowiseBackend(root, binary=cfg.backend.repowise_binary, ignore_globs=ignore)
    return FilesystemBackend(root, ignore_globs=ignore)


def all_backend_statuses(root: Path, cfg: MinionConfig) -> list[BackendStatus]:
    ignore = cfg.brief.ignore_globs
    return [
        FilesystemBackend(root, ignore_globs=ignore).status(),
        RepowiseBackend(root, binary=cfg.backend.repowise_binary, ignore_globs=ignore).status(),
    ]
