from __future__ import annotations

from pathlib import Path

from minion.backends.filesystem import FilesystemBackend
from minion.brief import rank_files, render_brief, write_brief
from minion.config import MinionConfig
from minion.repo import gather_repo_info
from minion.teacher.noop import NoopTeacher


def test_rank_files_prefers_path_match(tmp_repo: Path) -> None:
    fs = FilesystemBackend(tmp_repo, ignore_globs=[])
    files = fs.list_files()
    ranked = rank_files(files, "implement JWT auth flow", max_files=10)
    top = ranked[0].file.relpath
    assert "auth" in top
    # billing.py should not lead the ranking
    assert ranked[0].score > next(
        r.score for r in ranked if "billing" in r.file.relpath
    )


def test_render_brief_includes_task_and_stack(tmp_git_repo: Path) -> None:
    cfg = MinionConfig()
    cfg.backend.repowise_binary = "definitely-not-a-real-binary-zzz"
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
