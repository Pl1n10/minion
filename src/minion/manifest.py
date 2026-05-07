"""Minion manifest: state/manifest.json with init metadata."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import minion_dir


MANIFEST_RELPATH = "state/manifest.json"


@dataclass
class BackendAvailability:
    name: str
    available: bool
    detail: str = ""
    version: str | None = None


@dataclass
class Manifest:
    version: int = 1
    initialized_at: str = ""
    last_updated_at: str = ""
    repo_root: str = ""
    git_branch: str | None = None
    git_head: str | None = None
    git_remote: str | None = None
    stack: list[str] = field(default_factory=list)
    backends: list[BackendAvailability] = field(default_factory=list)
    selected_backend: str = "filesystem"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        return cls(
            version=int(data.get("version", 1)),
            initialized_at=data.get("initialized_at", ""),
            last_updated_at=data.get("last_updated_at", ""),
            repo_root=data.get("repo_root", ""),
            git_branch=data.get("git_branch"),
            git_head=data.get("git_head"),
            git_remote=data.get("git_remote"),
            stack=list(data.get("stack") or []),
            backends=[
                BackendAvailability(**b) for b in (data.get("backends") or [])
            ],
            selected_backend=data.get("selected_backend", "filesystem"),
        )


def manifest_path(repo_root: Path) -> Path:
    return minion_dir(repo_root) / MANIFEST_RELPATH


def load_manifest(repo_root: Path) -> Manifest | None:
    path = manifest_path(repo_root)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return Manifest.from_dict(json.load(fh))


def save_manifest(repo_root: Path, manifest: Manifest) -> Path:
    path = manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.last_updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("w", encoding="utf-8") as fh:
        json.dump(manifest.to_dict(), fh, indent=2, sort_keys=False)
    return path
