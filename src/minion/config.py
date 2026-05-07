"""Minion configuration handling.

The config lives at `.minion/config.yaml` inside the target repo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = "config.yaml"
MINION_DIR = ".minion"


@dataclass
class TeacherConfig:
    provider: str = "noop"
    model: str | None = None


@dataclass
class ReviewerConfig:
    provider: str = "noop"
    model: str | None = None


@dataclass
class BackendConfig:
    preferred: str = "auto"
    repowise_binary: str = "repowise"


@dataclass
class BriefConfig:
    max_files: int = 25
    max_file_bytes: int = 200_000
    ignore_globs: list[str] = field(
        default_factory=lambda: [
            ".git/**",
            ".venv/**",
            "venv/**",
            "node_modules/**",
            "dist/**",
            "build/**",
            "__pycache__/**",
            ".minion/**",
            "*.lock",
            "*.min.js",
            "*.map",
        ]
    )


@dataclass
class MinionConfig:
    version: int = 1
    backend: BackendConfig = field(default_factory=BackendConfig)
    teacher: TeacherConfig = field(default_factory=TeacherConfig)
    reviewer: ReviewerConfig = field(default_factory=ReviewerConfig)
    brief: BriefConfig = field(default_factory=BriefConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MinionConfig:
        return cls(
            version=int(data.get("version", 1)),
            backend=BackendConfig(**(data.get("backend") or {})),
            teacher=TeacherConfig(**(data.get("teacher") or {})),
            reviewer=ReviewerConfig(**(data.get("reviewer") or {})),
            brief=BriefConfig(**(data.get("brief") or {})),
        )


def config_path(repo_root: Path) -> Path:
    return repo_root / MINION_DIR / CONFIG_FILENAME


def minion_dir(repo_root: Path) -> Path:
    return repo_root / MINION_DIR


def load_config(repo_root: Path) -> MinionConfig:
    path = config_path(repo_root)
    if not path.exists():
        return MinionConfig()
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return MinionConfig.from_dict(data)


def save_config(repo_root: Path, cfg: MinionConfig) -> Path:
    path = config_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg.to_dict(), fh, sort_keys=False)
    return path
