"""Repository introspection: git metadata and stack detection."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


STACK_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"],
    "node": ["package.json"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "dotnet": ["*.csproj", "*.fsproj", "*.sln"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
    "powershell": ["*.psd1", "*.psm1"],
    "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"],
    "terraform": ["*.tf"],
    "kubernetes": ["kustomization.yaml", "Chart.yaml"],
}


@dataclass
class GitInfo:
    is_git: bool = False
    branch: str | None = None
    head: str | None = None
    remote: str | None = None


@dataclass
class RepoInfo:
    root: Path
    git: GitInfo = field(default_factory=GitInfo)
    stack: list[str] = field(default_factory=list)
    file_count: int = 0


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def detect_git(root: Path) -> GitInfo:
    if not (root / ".git").exists():
        return GitInfo()
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    head = _run_git(["rev-parse", "HEAD"], root)
    remote = _run_git(["config", "--get", "remote.origin.url"], root)
    return GitInfo(is_git=True, branch=branch, head=head, remote=remote)


def detect_stack(root: Path) -> list[str]:
    found: list[str] = []
    for stack, patterns in STACK_MARKERS.items():
        for pat in patterns:
            if "*" in pat:
                if any(root.glob(pat)) or any(root.glob(f"**/{pat}")):
                    found.append(stack)
                    break
            else:
                if (root / pat).exists():
                    found.append(stack)
                    break
    return found


def find_repo_root(start: Path) -> Path:
    """Walk up to find a git root; fall back to start if none."""
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cur


def gather_repo_info(root: Path) -> RepoInfo:
    return RepoInfo(
        root=root,
        git=detect_git(root),
        stack=detect_stack(root),
    )
