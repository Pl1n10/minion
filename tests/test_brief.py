from __future__ import annotations

from pathlib import Path

from minion.backends.filesystem import FilesystemBackend
from minion.brief import rank_files, render_brief, write_brief
from minion.config import MinionConfig
from minion.repo import gather_repo_info
from minion.teacher.noop import NoopTeacher


def _cfg(max_files: int = 10) -> MinionConfig:
    cfg = MinionConfig()
    cfg.brief.max_files = max_files
    cfg.backend.repowise_binary = "definitely-not-a-real-binary-zzz"
    return cfg


def test_rank_files_prefers_path_match(tmp_repo: Path) -> None:
    fs = FilesystemBackend(tmp_repo, ignore_globs=[])
    files = fs.list_files()
    ranked = rank_files(files, "implement JWT auth flow", _cfg())
    top = ranked[0].file.relpath
    assert "auth" in top
    assert ranked[0].score > next(
        r.score for r in ranked if "billing" in r.file.relpath
    )


def test_rank_files_uses_content_when_root_provided(tmp_path: Path) -> None:
    """Files whose path doesn't mention tokens still rank if their content does."""
    (tmp_path / "alpha.py").write_text(
        "def handle_payment():\n    # process JWT-signed payload\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "beta.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    fs = FilesystemBackend(tmp_path, ignore_globs=[])
    files = fs.list_files()

    # Without repo_root: only path-based scoring → tie or beta wins (none match path)
    cfg = _cfg()
    no_content = rank_files(files, "JWT signing", cfg)
    # Neither path matches "jwt"/"signing", so rankings come from generic source-file boost
    assert all("alpha.py" not in r.reasons for r in no_content for r in [r])

    # With repo_root: alpha.py wins because content matches
    with_content = rank_files(files, "JWT signing", cfg, repo_root=tmp_path)
    assert with_content[0].file.relpath == "alpha.py"
    reasons = " ".join(with_content[0].reasons)
    assert "content matches" in reasons
    assert "jwt" in reasons


def test_rank_files_skips_oversize_and_binary(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("auth\n" * 200_000, encoding="utf-8")  # > default max
    (tmp_path / "bin.dat").write_bytes(b"\x00\x01\x02jwt\x00")
    (tmp_path / "small.py").write_text("def auth(): pass\n", encoding="utf-8")
    fs = FilesystemBackend(tmp_path, ignore_globs=[])
    cfg = _cfg()
    cfg.brief.max_file_bytes = 1_000
    ranked = rank_files(fs.list_files(), "auth", cfg, repo_root=tmp_path)
    paths = [r.file.relpath for r in ranked]
    assert "small.py" in paths
    # big.py path contains no token; with content skipped it must drop out
    assert "big.py" not in paths
    assert "bin.dat" not in paths


def test_render_brief_includes_snippets_for_relevant_small_files(tmp_git_repo: Path) -> None:
    cfg = _cfg()
    fs = FilesystemBackend(tmp_git_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_git_repo)
    md = render_brief(
        task="add JWT auth",
        repo_info=info,
        backend=fs,
        teacher=NoopTeacher(),
        cfg=cfg,
    )
    assert "## Snippets" in md
    assert "src/auth.py" in md
    assert "```python" in md
    assert "login_with_jwt" in md  # actual file content reproduced as snippet


def test_render_brief_excludes_minion_dir(tmp_git_repo: Path) -> None:
    """Files under .minion/ must never leak into the brief, even if they match."""
    minion_path = tmp_git_repo / ".minion"
    minion_path.mkdir()
    (minion_path / "secret-auth.md").write_text("# auth jwt jwt jwt\n", encoding="utf-8")
    cfg = _cfg()
    fs = FilesystemBackend(tmp_git_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_git_repo)
    md = render_brief(
        task="add JWT auth",
        repo_info=info,
        backend=fs,
        teacher=NoopTeacher(),
        cfg=cfg,
    )
    assert "secret-auth" not in md
    assert ".minion/secret-auth.md" not in md
    # ranked file list should never reference anything under .minion/
    ranked_section = md.split("## Likely relevant files", 1)[1].split("##", 1)[0]
    assert ".minion/" not in ranked_section


def test_render_brief_includes_task_and_stack(tmp_git_repo: Path) -> None:
    cfg = _cfg()
    fs = FilesystemBackend(tmp_git_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_git_repo)
    md = render_brief(
        task="add JWT auth",
        repo_info=info,
        backend=fs,
        teacher=NoopTeacher(),
        cfg=cfg,
    )
    assert "add JWT auth" in md
    assert "python" in md
    assert "Likely relevant files" in md


def test_write_brief_creates_timestamped_file(tmp_path: Path) -> None:
    out = write_brief(tmp_path / "briefs", "# hi")
    assert out.exists()
    assert out.parent.name == "briefs"
    assert out.suffix == ".md"
