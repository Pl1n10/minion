"""Knowledge-pack generator for `.minion/MINION.md`.

`minion teach` regenerates everything in MINION.md *except* the
section between MINION:USER-NOTES markers, which is preserved across
runs so users can keep durable notes alongside the auto-generated parts.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.resources import files as resource_files
from pathlib import Path

from .backends.base import FileEntry
from .config import MinionConfig
from .repo import RepoInfo

USER_NOTES_START = "<!-- MINION:USER-NOTES:START -->"
USER_NOTES_END = "<!-- MINION:USER-NOTES:END -->"

DEFAULT_USER_NOTES = (
    "_(your durable repo notes go here — preserved across "
    "`minion teach` runs)_"
)

ENTRYPOINT_NAMES = {
    "main.py", "app.py", "cli.py", "__main__.py", "manage.py",
    "server.py", "wsgi.py", "asgi.py", "run.py",
    "index.js", "index.ts", "main.ts", "server.js", "server.ts",
    "app.ts", "app.js",
    "main.go",
    "main.rs", "lib.rs",
}

CONFIG_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "Pipfile.lock", "uv.lock", "poetry.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "compose.yml", "compose.yaml", "Makefile",
    ".env.example", ".env.sample",
    ".pre-commit-config.yaml", "kustomization.yaml", "Chart.yaml",
    ".gitignore", ".dockerignore",
}

CONFIG_NAME_PREFIXES = (
    "vite.config.", "webpack.config.", "next.config.",
    "tailwind.config.", "postcss.config.",
)

DOC_NAME_PREFIXES = (
    "README", "CHANGELOG", "CONTRIBUTING", "LICENSE",
    "CODE_OF_CONDUCT", "SECURITY",
)


@dataclass(frozen=True)
class PlaybookEntry:
    name: str
    description: str
    path: str


@dataclass
class KnowledgePack:
    project_name: str
    project_description: str
    stack: list[str] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    suggested_first_files: list[str] = field(default_factory=list)
    ignored_globs: list[str] = field(default_factory=list)
    playbooks: list[PlaybookEntry] = field(default_factory=list)
    file_count: int = 0
    taught_at: str = ""


def _safe_toml(path: Path) -> dict | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None


def _safe_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _project_meta(root: Path) -> tuple[str, str]:
    """Best-effort name + description from common manifest files."""
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        data = _safe_toml(pyproject) or {}
        proj = data.get("project") or {}
        if proj.get("name") or proj.get("description"):
            return proj.get("name") or root.name, proj.get("description") or ""

    pkg = root / "package.json"
    if pkg.exists():
        data = _safe_json(pkg) or {}
        if data.get("name") or data.get("description"):
            return data.get("name") or root.name, data.get("description") or ""

    cargo = root / "Cargo.toml"
    if cargo.exists():
        data = _safe_toml(cargo) or {}
        meta = data.get("package") or {}
        if meta.get("name") or meta.get("description"):
            return meta.get("name") or root.name, meta.get("description") or ""

    return root.name, ""


def _is_test_file(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in {"tests", "test", "__tests__", "spec"} for p in parts[:-1]):
        return True
    name = parts[-1]
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py") or name.endswith("_test.go"):
        return True
    test_suffixes = (
        ".test.js", ".test.ts", ".test.tsx", ".test.jsx",
        ".spec.js", ".spec.ts", ".spec.tsx", ".spec.jsx",
    )
    return any(name.endswith(suf) for suf in test_suffixes)


def _is_doc_file(rel: str) -> bool:
    parts = rel.split("/")
    if parts[0] == "docs":
        return True
    name = parts[-1]
    if any(name.startswith(p) for p in DOC_NAME_PREFIXES):
        return True
    if len(parts) == 1 and name.endswith(".md"):
        return True
    return False


def _is_config_file(rel: str) -> bool:
    name = Path(rel).name
    if name in CONFIG_NAMES:
        return True
    if rel.startswith(".github/workflows/") and (
        name.endswith(".yml") or name.endswith(".yaml")
    ):
        return True
    if name.endswith(".tf"):
        return True
    return any(name.startswith(p) for p in CONFIG_NAME_PREFIXES)


def _suggest_first_files(
    entrypoints: list[str],
    configs: list[str],
    docs: list[str],
    limit: int = 6,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        if p and p not in seen and len(out) < limit:
            out.append(p)
            seen.add(p)

    # README first if present
    for d in docs:
        if Path(d).name.lower().startswith("readme"):
            add(d)
            break

    # Then top entrypoints, preferring shallow ones
    for e in sorted(entrypoints, key=lambda p: (p.count("/"), p)):
        add(e)

    # Then primary manifest files in priority order
    primary = ["pyproject.toml", "package.json", "go.mod", "Cargo.toml",
               "Dockerfile", "Makefile"]
    for needle in primary:
        for c in configs:
            if Path(c).name == needle:
                add(c)
                break

    return out


def _extract_playbook_description(text: str) -> str:
    """First sentence of the leading blockquote, used as a short description."""
    quote_lines: list[str] = []
    in_quote = False
    for line in text.splitlines():
        if line.startswith(">"):
            in_quote = True
            quote_lines.append(line.lstrip(">").strip())
        elif in_quote:
            break
    joined = " ".join(q for q in quote_lines if q)
    if not joined:
        return ""
    first = joined.split(". ", 1)[0].rstrip(".")
    return first + "."


def _discover_playbooks() -> list[PlaybookEntry]:
    """Enumerate built-in playbook templates bundled with the package."""
    root = resource_files("minion") / "templates" / "playbooks"
    if not root.is_dir():
        return []
    out: list[PlaybookEntry] = []
    for entry in root.iterdir():
        if not entry.name.endswith(".md.tmpl"):
            continue
        slug = entry.name.removesuffix(".md.tmpl")
        try:
            text = entry.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.append(
            PlaybookEntry(
                name=slug,
                description=_extract_playbook_description(text),
                path=str(entry),
            )
        )
    return sorted(out, key=lambda p: p.name)


def gather_pack(
    root: Path,
    repo_info: RepoInfo,
    files: list[FileEntry],
    cfg: MinionConfig,
) -> KnowledgePack:
    name, desc = _project_meta(root)

    entrypoints: list[str] = []
    config_files: list[str] = []
    test_files: list[str] = []
    doc_files: list[str] = []

    for f in files:
        rel = f.relpath
        bn = Path(rel).name
        if bn in ENTRYPOINT_NAMES:
            entrypoints.append(rel)
        if _is_test_file(rel):
            test_files.append(rel)
            continue  # tests are listed separately, don't double-classify
        if _is_config_file(rel):
            config_files.append(rel)
        if _is_doc_file(rel):
            doc_files.append(rel)

    entrypoints.sort()
    config_files.sort()
    test_files.sort()
    doc_files.sort()

    return KnowledgePack(
        project_name=name,
        project_description=desc,
        stack=list(repo_info.stack),
        entrypoints=entrypoints,
        config_files=config_files,
        test_files=test_files,
        doc_files=doc_files,
        suggested_first_files=_suggest_first_files(entrypoints, config_files, doc_files),
        ignored_globs=list(cfg.brief.ignore_globs),
        playbooks=_discover_playbooks(),
        file_count=len(files),
        taught_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def extract_user_notes(existing: str) -> str | None:
    """Return the text between USER-NOTES markers, or None if not present."""
    if USER_NOTES_START not in existing or USER_NOTES_END not in existing:
        return None
    s = existing.index(USER_NOTES_START) + len(USER_NOTES_START)
    e = existing.index(USER_NOTES_END)
    if e <= s:
        return None
    return existing[s:e].strip("\n")


def _bullet_list(items: list[str], empty: str = "_(none detected)_") -> str:
    if not items:
        return empty
    return "\n".join(f"- `{item}`" for item in items)


def _playbook_bullets(items: list[PlaybookEntry]) -> str:
    if not items:
        return "_(none bundled)_"
    return "\n".join(
        f"- **{p.name}** — {p.description} Path: `{p.path}`" for p in items
    )


def render_minion_md(pack: KnowledgePack, user_notes: str) -> str:
    if pack.project_description:
        header_line = f"**{pack.project_name}** — {pack.project_description}"
    else:
        header_line = f"**{pack.project_name}**"
    stack_line = ", ".join(pack.stack) if pack.stack else "_(unknown)_"

    sections = [
        "# MINION.md",
        "",
        "> Auto-generated by `minion teach`. Everything outside the",
        "> `MINION:USER-NOTES` markers is regenerated each run; the",
        "> user-notes block is preserved.",
        "",
        USER_NOTES_START,
        "",
        user_notes,
        "",
        USER_NOTES_END,
        "",
        "## Project summary",
        "",
        header_line,
        "",
        f"- Files indexed by selected backend: {pack.file_count}",
        "",
        "## Detected stack",
        "",
        stack_line,
        "",
        "## Key entrypoints",
        "",
        _bullet_list(pack.entrypoints),
        "",
        "## Important config files",
        "",
        _bullet_list(pack.config_files),
        "",
        "## Test files",
        "",
        _bullet_list(pack.test_files),
        "",
        "## Documentation files",
        "",
        _bullet_list(pack.doc_files),
        "",
        "## Suggested first files to inspect",
        "",
        _bullet_list(pack.suggested_first_files, empty="_(no suggestions)_"),
        "",
        "## Do-not-index / ignored paths",
        "",
        _bullet_list(pack.ignored_globs, empty="_(none)_"),
        "",
        "## Available playbooks",
        "",
        "Prescriptive markdown for repetitive setup actions, bundled with Minion.",
        "Read the relevant one **before** doing the task — Minion does not execute them.",
        "If an operator-specific resolved copy exists (e.g. under",
        "`<minion-checkout>/playbooks/<name>.md`), prefer it: it has parameter",
        "values pre-filled for that operator.",
        "",
        _playbook_bullets(pack.playbooks),
        "",
        "---",
        "",
        f"_Last taught: {pack.taught_at}_",
        "",
    ]
    return "\n".join(sections)
