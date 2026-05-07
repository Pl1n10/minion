from __future__ import annotations

from pathlib import Path

from minion.backends import all_backend_statuses, select_backend
from minion.backends.filesystem import FilesystemBackend
from minion.backends.repowise import RepowiseBackend
from minion.config import MinionConfig


def test_filesystem_backend_lists_files(tmp_repo: Path) -> None:
    fs = FilesystemBackend(tmp_repo, ignore_globs=[".git/**"])
    files = fs.list_files()
    rels = {f.relpath for f in files}
    assert "src/auth.py" in rels
    assert "package.json" in rels


def test_filesystem_backend_respects_ignore(tmp_repo: Path) -> None:
    (tmp_repo / "node_modules").mkdir()
    (tmp_repo / "node_modules" / "junk.js").write_text("//", encoding="utf-8")
    fs = FilesystemBackend(tmp_repo, ignore_globs=["node_modules/**"])
    rels = {f.relpath for f in fs.list_files()}
    assert not any(r.startswith("node_modules/") for r in rels)


def test_filesystem_assigns_language(tmp_repo: Path) -> None:
    fs = FilesystemBackend(tmp_repo, ignore_globs=[])
    langs = {f.relpath: f.language for f in fs.list_files()}
    assert langs.get("src/auth.py") == "python"
    assert langs.get("package.json") == "json"


def test_repowise_backend_status_when_missing(tmp_repo: Path) -> None:
    backend = RepowiseBackend(tmp_repo, binary="definitely-not-a-real-binary-zzz")
    s = backend.status()
    assert s.available is False
    assert "not found" in s.detail


def test_select_backend_auto_falls_back_to_filesystem(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    cfg.backend.repowise_binary = "definitely-not-a-real-binary-zzz"
    backend = select_backend(tmp_repo, cfg)
    assert backend.name == "filesystem"


def test_all_backend_statuses_includes_both(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    cfg.backend.repowise_binary = "definitely-not-a-real-binary-zzz"
    statuses = all_backend_statuses(tmp_repo, cfg)
    names = {s.name for s in statuses}
    assert {"filesystem", "repowise"} <= names
