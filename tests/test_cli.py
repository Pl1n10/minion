from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minion.cli import app

runner = CliRunner()


def test_init_creates_layout(tmp_git_repo: Path) -> None:
    result = runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    assert result.exit_code == 0, result.stdout
    mdir = tmp_git_repo / ".minion"
    assert (mdir / "MINION.md").exists()
    assert (mdir / "teacher-plan.md").exists()
    assert (mdir / "config.yaml").exists()
    assert (mdir / "state" / "manifest.json").exists()
    manifest = json.loads((mdir / "state" / "manifest.json").read_text())
    assert manifest["initialized_at"]
    assert manifest["selected_backend"] in {"filesystem", "repowise"}
    assert any(b["name"] == "repowise" for b in manifest["backends"])


def test_init_is_idempotent(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    minion_md = tmp_git_repo / ".minion" / "MINION.md"
    minion_md.write_text("# custom edits\n", encoding="utf-8")
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    assert minion_md.read_text() == "# custom edits\n"


def test_init_force_resets_files(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    minion_md = tmp_git_repo / ".minion" / "MINION.md"
    minion_md.write_text("# custom\n", encoding="utf-8")
    runner.invoke(app, ["init", "--path", str(tmp_git_repo), "--force"])
    assert "# MINION.md" in minion_md.read_text()


def test_status_without_init(tmp_repo: Path) -> None:
    result = runner.invoke(app, ["status", "--path", str(tmp_repo)])
    assert result.exit_code == 0
    assert "minion init" in result.stdout.lower() or "no" in result.stdout.lower()


def test_status_after_init(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    result = runner.invoke(app, ["status", "--path", str(tmp_git_repo)])
    assert result.exit_code == 0
    assert "filesystem" in result.stdout
    assert "repowise" in result.stdout


def test_brief_creates_markdown(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    result = runner.invoke(
        app, ["brief", "add JWT auth flow", "--path", str(tmp_git_repo)]
    )
    assert result.exit_code == 0, result.stdout
    briefs = list((tmp_git_repo / ".minion" / "briefs").glob("*-brief.md"))
    assert len(briefs) == 1
    body = briefs[0].read_text()
    assert "add JWT auth flow" in body


def test_brief_without_init_fails(tmp_repo: Path) -> None:
    result = runner.invoke(app, ["brief", "anything", "--path", str(tmp_repo)])
    assert result.exit_code == 1
