"""Brief generation: rank files for a task and emit a markdown brief."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from .backends.base import FileEntry, RepoBackend
from .config import MinionConfig
from .repo import RepoInfo
from .teacher import TeacherPlan, TeacherProvider


_STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "with",
    "add", "fix", "update", "make", "do", "is", "are", "be", "as", "by",
    "into", "from", "use", "using", "support", "feature", "implement",
    "this", "that", "it", "its", "we", "should", "can", "must", "needs",
    "need", "new", "old",
}

_SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".hpp", ".sh", ".ps1",
    ".sql", ".md",
}


@dataclass
class RankedFile:
    file: FileEntry
    score: float
    reasons: list[str]


def _tokenize(task: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", task.lower())
    return [t for t in raw if t not in _STOPWORDS]


def rank_files(
    files: list[FileEntry],
    task: str,
    max_files: int,
) -> list[RankedFile]:
    tokens = _tokenize(task)
    ranked: list[RankedFile] = []
    for f in files:
        rel = f.relpath.lower()
        score = 0.0
        reasons: list[str] = []

        for tok in tokens:
            if tok in rel:
                score += 3.0
                reasons.append(f"path matches '{tok}'")

        suffix = Path(rel).suffix
        if suffix in _SOURCE_EXTS:
            score += 0.5
            reasons.append("source file")

        # Penalize huge files (likely vendored)
        if f.size > 500_000:
            score -= 1.0
            reasons.append("large file (penalized)")

        # Boost likely entry points
        name = Path(rel).name
        if name in {"main.py", "main.go", "index.ts", "index.js", "app.py", "cli.py", "server.py"}:
            score += 1.0
            reasons.append("likely entry point")

        if score > 0:
            ranked.append(RankedFile(file=f, score=score, reasons=reasons))

    ranked.sort(key=lambda r: (-r.score, r.file.relpath))
    return ranked[:max_files]


def _format_ranked(ranked: list[RankedFile]) -> str:
    if not ranked:
        return "_No files matched task tokens. Either the task is too generic or the repo is empty._"
    lines = []
    for r in ranked:
        reasons = ", ".join(r.reasons)
        lines.append(f"- `{r.file.relpath}` — score {r.score:.1f} ({reasons})")
    return "\n".join(lines)


def _format_plan(plan: TeacherPlan) -> str:
    out = [f"**Summary:** {plan.summary}", "", "**Steps:**"]
    out.extend(f"- {s}" for s in plan.steps)
    out.append("")
    out.append("**Acceptance:**")
    out.extend(f"- {a}" for a in plan.acceptance)
    out.append("")
    out.append("**Risks:**")
    out.extend(f"- {r}" for r in plan.risks)
    return "\n".join(out)


def _load_template(name: str) -> str:
    return resources.files("minion.templates").joinpath(name).read_text(encoding="utf-8")


def render_brief(
    task: str,
    repo_info: RepoInfo,
    backend: RepoBackend,
    teacher: TeacherProvider,
    cfg: MinionConfig,
    minion_md: str = "",
) -> str:
    files = backend.list_files()
    ranked = rank_files(files, task, cfg.brief.max_files)
    status = backend.status()
    plan = teacher.plan(task, context=minion_md)

    tmpl = _load_template("brief.md.tmpl")
    return tmpl.format(
        task=task,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        backend_name=status.name,
        backend_detail=status.detail,
        repo_root=repo_info.root,
        branch=repo_info.git.branch or "(no git)",
        head=(repo_info.git.head or "")[:12] or "(no git)",
        stack=", ".join(repo_info.stack) or "unknown",
        ranked_files=_format_ranked(ranked),
        teacher_plan=_format_plan(plan),
    )


def write_brief(target_dir: Path, content: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"{ts}-brief.md"
    path.write_text(content, encoding="utf-8")
    return path
