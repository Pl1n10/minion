from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A throwaway repo with a minimal Python+Node footprint."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n', encoding="utf-8"
    )
    (tmp_path / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text(
        "def login_with_jwt():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "src" / "billing.py").write_text(
        "def invoice():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def tmp_git_repo(tmp_repo: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."],
        cwd=tmp_repo,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=tmp_repo,
        check=True,
    )
    return tmp_repo
