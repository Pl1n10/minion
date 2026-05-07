"""Minion CLI."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .backends import all_backend_statuses, select_backend
from .brief import render_brief, write_brief
from .config import MinionConfig, config_path, load_config, minion_dir, save_config
from .manifest import BackendAvailability, Manifest, load_manifest, save_manifest
from .repo import find_repo_root, gather_repo_info
from .reviewer import select_reviewer
from .teacher import select_teacher

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Minion: local-first repo intelligence coprocessor for AI coding agents.",
)
console = Console()

BRIEFS_DIR = "briefs"


def _load_template(name: str) -> str:
    return resources.files("minion.templates").joinpath(name).read_text(encoding="utf-8")


def _resolve_root(path: Optional[Path]) -> Path:
    start = path.resolve() if path else Path.cwd()
    return find_repo_root(start)


@app.command()
def init(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        help="Directory to initialize (defaults to git root or CWD).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing .minion/ files."
    ),
) -> None:
    """Initialize `.minion/` in the current repo."""
    root = _resolve_root(path)
    mdir = minion_dir(root)
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "state").mkdir(parents=True, exist_ok=True)
    (mdir / BRIEFS_DIR).mkdir(parents=True, exist_ok=True)

    # Config
    cfg_path = config_path(root)
    if not cfg_path.exists() or force:
        save_config(root, MinionConfig())

    cfg = load_config(root)

    # MINION.md and teacher-plan.md
    minion_md = mdir / "MINION.md"
    if not minion_md.exists() or force:
        minion_md.write_text(_load_template("MINION.md.tmpl"), encoding="utf-8")

    plan_md = mdir / "teacher-plan.md"
    if not plan_md.exists() or force:
        plan_md.write_text(_load_template("teacher-plan.md.tmpl"), encoding="utf-8")

    # Manifest
    info = gather_repo_info(root)
    statuses = all_backend_statuses(root, cfg)
    selected = select_backend(root, cfg).name

    manifest = Manifest(
        initialized_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        repo_root=str(root),
        git_branch=info.git.branch,
        git_head=info.git.head,
        git_remote=info.git.remote,
        stack=info.stack,
        backends=[
            BackendAvailability(
                name=s.name,
                available=s.available,
                detail=s.detail,
                version=s.version,
            )
            for s in statuses
        ],
        selected_backend=selected,
    )
    save_manifest(root, manifest)

    console.print(f"[green]Initialized[/green] minion in [bold]{mdir}[/bold]")
    console.print(f"  config:    {cfg_path.relative_to(root)}")
    console.print(f"  manifest:  {(mdir / 'state' / 'manifest.json').relative_to(root)}")
    console.print(f"  selected backend: [cyan]{selected}[/cyan]")
    if info.stack:
        console.print(f"  detected stack: {', '.join(info.stack)}")
    else:
        console.print("  detected stack: [yellow]unknown[/yellow]")


@app.command()
def brief(
    task: str = typer.Argument(..., help="Short description of the task."),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Generate a markdown brief for a task."""
    root = _resolve_root(path)
    mdir = minion_dir(root)
    if not mdir.exists():
        console.print(
            "[red]No .minion/ found.[/red] Run `minion init` first."
        )
        raise typer.Exit(code=1)

    cfg = load_config(root)
    backend = select_backend(root, cfg)
    teacher = select_teacher(cfg)
    _ = select_reviewer(cfg)  # not used yet, but exercises the wiring

    minion_md_path = mdir / "MINION.md"
    minion_md = (
        minion_md_path.read_text(encoding="utf-8") if minion_md_path.exists() else ""
    )

    info = gather_repo_info(root)
    content = render_brief(
        task=task,
        repo_info=info,
        backend=backend,
        teacher=teacher,
        cfg=cfg,
        minion_md=minion_md,
    )
    out_path = write_brief(mdir / BRIEFS_DIR, content)
    console.print(f"[green]Brief written[/green]: {out_path.relative_to(root)}")
    typer.echo(str(out_path))


@app.command()
def status(
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show minion status for the current repo."""
    root = _resolve_root(path)
    mdir = minion_dir(root)

    table = Table(title="Minion status", show_header=False, box=None)
    table.add_row("repo root", str(root))
    table.add_row(".minion present", "[green]yes[/green]" if mdir.exists() else "[red]no[/red]")

    if not mdir.exists():
        console.print(table)
        console.print("[yellow]Run `minion init` to set up.[/yellow]")
        return

    cfg = load_config(root)
    manifest = load_manifest(root)
    info = gather_repo_info(root)

    if manifest:
        table.add_row("initialized at", manifest.initialized_at or "?")
        table.add_row("last updated", manifest.last_updated_at or "?")
        table.add_row("selected backend", manifest.selected_backend)
        table.add_row(
            "stack (manifest)",
            ", ".join(manifest.stack) if manifest.stack else "unknown",
        )
    else:
        table.add_row("manifest", "[yellow]missing[/yellow]")

    table.add_row(
        "stack (live)",
        ", ".join(info.stack) if info.stack else "unknown",
    )
    table.add_row(
        "git branch",
        info.git.branch or "[dim]-[/dim]",
    )

    console.print(table)

    backend_table = Table(title="Backends", show_header=True, header_style="bold")
    backend_table.add_column("name")
    backend_table.add_column("available")
    backend_table.add_column("detail")
    backend_table.add_column("version")
    for s in all_backend_statuses(root, cfg):
        backend_table.add_row(
            s.name,
            "[green]yes[/green]" if s.available else "[red]no[/red]",
            s.detail,
            s.version or "-",
        )
    console.print(backend_table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
