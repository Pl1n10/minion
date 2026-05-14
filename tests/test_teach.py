from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minion.backends.filesystem import FilesystemBackend
from minion.cli import app
from minion.config import MinionConfig
from minion.repo import gather_repo_info
from minion.teach import (
    USER_NOTES_END,
    USER_NOTES_START,
    extract_user_notes,
    gather_pack,
    render_minion_md,
)

runner = CliRunner()


# ---------- unit tests on the generator ----------


def test_extract_user_notes_returns_content_between_markers() -> None:
    text = (
        "# MINION.md\n"
        f"{USER_NOTES_START}\n"
        "hello world\n"
        "second line\n"
        f"{USER_NOTES_END}\n"
        "trailing trash\n"
    )
    assert extract_user_notes(text) == "hello world\nsecond line"


def test_extract_user_notes_returns_none_without_markers() -> None:
    assert extract_user_notes("# bare\n") is None


def test_extract_user_notes_returns_none_when_inverted() -> None:
    text = f"# x\n{USER_NOTES_END}\n{USER_NOTES_START}\n"
    assert extract_user_notes(text) is None


def test_gather_pack_classifies_files(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    fs = FilesystemBackend(tmp_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_repo)
    pack = gather_pack(tmp_repo, info, fs.list_files(), cfg)

    assert "pyproject.toml" in pack.config_files
    assert "package.json" in pack.config_files
    assert "README.md" in pack.doc_files
    assert pack.project_name == "demo"  # from fixture pyproject
    assert pack.taught_at  # ISO datetime string
    assert pack.file_count > 0
    assert pack.suggested_first_files
    assert pack.suggested_first_files[0] == "README.md"


def test_gather_pack_finds_tests_and_entrypoints(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\n', encoding="utf-8"
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_thing.py").write_text("def test_x(): pass\n", encoding="utf-8")

    cfg = MinionConfig()
    fs = FilesystemBackend(tmp_path, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_path)
    pack = gather_pack(tmp_path, info, fs.list_files(), cfg)

    assert "main.py" in pack.entrypoints
    assert "tests/test_thing.py" in pack.test_files
    # test files must not be double-counted as configs
    assert "tests/test_thing.py" not in pack.config_files


def test_gather_pack_discovers_builtin_playbooks(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    fs = FilesystemBackend(tmp_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_repo)
    pack = gather_pack(tmp_repo, info, fs.list_files(), cfg)

    names = [p.name for p in pack.playbooks]
    assert "git-setup" in names, f"git-setup playbook missing, got {names}"
    git_setup = next(p for p in pack.playbooks if p.name == "git-setup")
    assert git_setup.description, "git-setup playbook should have a description"
    assert git_setup.path.endswith("git-setup.md.tmpl"), (
        f"playbook path should point at the .tmpl file, got {git_setup.path!r}"
    )


def test_render_minion_md_lists_playbooks(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    fs = FilesystemBackend(tmp_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_repo)
    pack = gather_pack(tmp_repo, info, fs.list_files(), cfg)
    md = render_minion_md(pack, "_notes_")

    assert "## Available playbooks" in md
    assert "**git-setup**" in md
    assert "git-setup.md.tmpl" in md, "rendered section should expose the playbook path"


def test_render_minion_md_contains_all_sections(tmp_repo: Path) -> None:
    cfg = MinionConfig()
    fs = FilesystemBackend(tmp_repo, ignore_globs=cfg.brief.ignore_globs)
    info = gather_repo_info(tmp_repo)
    pack = gather_pack(tmp_repo, info, fs.list_files(), cfg)
    md = render_minion_md(pack, "_my notes_")

    for section in (
        "## Project summary",
        "## Detected stack",
        "## Key entrypoints",
        "## Important config files",
        "## Test files",
        "## Documentation files",
        "## Suggested first files to inspect",
        "## Do-not-index / ignored paths",
        "## Available playbooks",
    ):
        assert section in md, f"missing {section}"
    assert USER_NOTES_START in md
    assert USER_NOTES_END in md
    assert "_my notes_" in md
    assert "_Last taught:" in md


# ---------- CLI behaviour ----------


def test_teach_creates_useful_minion_md(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    result = runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    assert result.exit_code == 0, result.stdout

    md = (tmp_git_repo / ".minion" / "MINION.md").read_text(encoding="utf-8")
    assert "## Project summary" in md
    assert "## Key entrypoints" in md
    assert "pyproject.toml" in md
    assert "package.json" in md
    assert "README.md" in md
    assert USER_NOTES_START in md
    assert USER_NOTES_END in md


def test_teach_preserves_user_notes(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    minion_md = tmp_git_repo / ".minion" / "MINION.md"
    custom = (
        "# MINION.md\n\n"
        f"{USER_NOTES_START}\n"
        "MY CUSTOM PROJECT NOTES\n"
        "second line that must survive\n"
        f"{USER_NOTES_END}\n\n"
        "this trailing junk must be wiped on teach\n"
    )
    minion_md.write_text(custom, encoding="utf-8")

    result = runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    assert result.exit_code == 0

    md = minion_md.read_text(encoding="utf-8")
    assert "MY CUSTOM PROJECT NOTES" in md
    assert "second line that must survive" in md
    assert "this trailing junk must be wiped on teach" not in md
    assert "## Project summary" in md


def test_teach_dry_run_does_not_modify_file(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    minion_md = tmp_git_repo / ".minion" / "MINION.md"
    before = minion_md.read_text(encoding="utf-8")

    result = runner.invoke(app, ["teach", "--path", str(tmp_git_repo), "--dry-run"])
    assert result.exit_code == 0
    assert minion_md.read_text(encoding="utf-8") == before
    # rendered markdown must reach stdout
    assert "## Project summary" in result.stdout
    assert USER_NOTES_START in result.stdout


def test_teach_without_init_fails(tmp_repo: Path) -> None:
    result = runner.invoke(app, ["teach", "--path", str(tmp_repo)])
    assert result.exit_code == 1


def test_teach_does_not_index_minion_dir(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    # Plant a tempting file inside .minion that should be ignored
    (tmp_git_repo / ".minion" / "secret.md").write_text("# secret\n", encoding="utf-8")

    runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    md = (tmp_git_repo / ".minion" / "MINION.md").read_text(encoding="utf-8")
    assert "secret.md" not in md
    assert ".minion/secret" not in md


def test_teach_idempotent_user_notes_round_trip(tmp_git_repo: Path) -> None:
    """teach → edit notes → teach again should keep the latest notes."""
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    minion_md = tmp_git_repo / ".minion" / "MINION.md"

    md = minion_md.read_text(encoding="utf-8")
    s = md.index(USER_NOTES_START) + len(USER_NOTES_START)
    e = md.index(USER_NOTES_END)
    new_md = md[:s] + "\n\nNOTES_v2\n\n" + md[e:]
    minion_md.write_text(new_md, encoding="utf-8")

    runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    final = minion_md.read_text(encoding="utf-8")
    assert "NOTES_v2" in final


def test_teach_summary_message_mentions_counts(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    result = runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    assert result.exit_code == 0
    # Check structured count display
    assert "configs:" in result.stdout
    assert "docs:" in result.stdout


def test_init_template_includes_user_notes_markers(tmp_git_repo: Path) -> None:
    """Make sure init seeds the markers so users can write notes pre-teach."""
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    md = (tmp_git_repo / ".minion" / "MINION.md").read_text(encoding="utf-8")
    assert USER_NOTES_START in md
    assert USER_NOTES_END in md


def test_teach_does_not_alter_manifest(tmp_git_repo: Path) -> None:
    runner.invoke(app, ["init", "--path", str(tmp_git_repo)])
    manifest_path = tmp_git_repo / ".minion" / "state" / "manifest.json"
    before = json.loads(manifest_path.read_text())
    runner.invoke(app, ["teach", "--path", str(tmp_git_repo)])
    after = json.loads(manifest_path.read_text())
    assert before == after
