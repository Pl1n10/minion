from __future__ import annotations

from pathlib import Path

from minion.repo import detect_git, detect_stack, find_repo_root, gather_repo_info


def test_detect_stack_python_node(tmp_repo: Path) -> None:
    stack = detect_stack(tmp_repo)
    assert "python" in stack
    assert "node" in stack


def test_detect_git_no_repo(tmp_repo: Path) -> None:
    assert detect_git(tmp_repo).is_git is False


def test_detect_git_with_repo(tmp_git_repo: Path) -> None:
    info = detect_git(tmp_git_repo)
    assert info.is_git is True
    assert info.head and len(info.head) >= 7


def test_find_repo_root_walks_up(tmp_git_repo: Path) -> None:
    nested = tmp_git_repo / "src"
    assert find_repo_root(nested) == tmp_git_repo


def test_gather_repo_info(tmp_git_repo: Path) -> None:
    info = gather_repo_info(tmp_git_repo)
    assert info.git.is_git
    assert info.stack
