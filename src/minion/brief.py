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

_CONTENT_MATCH_CAP = 5  # don't let one large file dominate via content hits
_CONTENT_MATCH_WEIGHT = 1.0
_PATH_MATCH_WEIGHT = 3.0


@dataclass
class RankedFile:
    file: FileEntry
    score: float
    reasons: list[str]
    content_hits: dict[str, int]  # token -> match count, for snippet selection


def _tokenize(task: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", task.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        if t in _STOPWORDS or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _read_text_safe(path: Path, max_bytes: int) -> str | None:
    """Read text content if path is within size budget and decodable as UTF-8."""
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size == 0 or size > max_bytes:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return None


def _count_token_hits(text: str, tokens: list[str]) -> dict[str, int]:
    """Count whole-word case-insensitive occurrences for each token."""
    hits: dict[str, int] = {}
    lower = text.lower()
    for tok in tokens:
        # word-ish boundary: letters/digits/underscore are word chars
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(tok)}(?![A-Za-z0-9_])")
        n = len(pattern.findall(lower))
        if n:
            hits[tok] = n
    return hits


def rank_files(
    files: list[FileEntry],
    task: str,
    cfg: MinionConfig,
    repo_root: Path | None = None,
) -> list[RankedFile]:
    """Rank files for the task by path and (when `repo_root` is given) content.

    Content scanning is bounded by `cfg.brief.max_file_bytes` and silently
    skipped for binary or oversize files.
    """
    tokens = _tokenize(task)
    max_files = cfg.brief.max_files
    max_bytes = cfg.brief.max_file_bytes

    ranked: list[RankedFile] = []
    for f in files:
        rel = f.relpath.lower()
        score = 0.0
        reasons: list[str] = []
        content_hits: dict[str, int] = {}

        for tok in tokens:
            if tok in rel:
                score += _PATH_MATCH_WEIGHT
                reasons.append(f"path matches '{tok}'")

        suffix = Path(rel).suffix
        if suffix in _SOURCE_EXTS:
            score += 0.5
            reasons.append("source file")

        if f.size > 500_000:
            score -= 1.0
            reasons.append("large file (penalized)")

        name = Path(rel).name
        if name in {"main.py", "main.go", "index.ts", "index.js", "app.py", "cli.py", "server.py"}:
            score += 1.0
            reasons.append("likely entry point")

        if repo_root is not None and tokens:
            text = _read_text_safe(repo_root / f.path, max_bytes)
            if text is not None:
                content_hits = _count_token_hits(text, tokens)
                for tok, n in content_hits.items():
                    capped = min(n, _CONTENT_MATCH_CAP)
                    score += _CONTENT_MATCH_WEIGHT * capped
                    suffix = "" if n == 1 else "s"
                    reasons.append(f"content matches '{tok}' ({n} hit{suffix})")

        if score > 0:
            ranked.append(
                RankedFile(file=f, score=score, reasons=reasons, content_hits=content_hits)
            )

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


def _extract_snippet(text: str, tokens: list[str], max_lines: int) -> str:
    """Pick a window around the first content match; fall back to the head of the file."""
    lines = text.splitlines()
    if not lines:
        return ""
    target = 0
    if tokens:
        token_re = re.compile(
            r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(t) for t in tokens) + r")(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        for i, line in enumerate(lines):
            if token_re.search(line):
                target = i
                break
    half = max_lines // 2
    start = max(0, target - half)
    end = min(len(lines), start + max_lines)
    start = max(0, end - max_lines)  # re-pad start if we hit the bottom
    excerpt = lines[start:end]
    prefix = f"… (lines {start + 1}-{end} of {len(lines)})\n" if start > 0 or end < len(lines) else ""
    return prefix + "\n".join(excerpt)


def _format_snippets(
    ranked: list[RankedFile],
    repo_root: Path,
    tokens: list[str],
    cfg: MinionConfig,
) -> str:
    if cfg.brief.max_snippet_files <= 0:
        return "_(snippets disabled)_"
    out: list[str] = []
    n_files = 0
    for r in ranked:
        if n_files >= cfg.brief.max_snippet_files:
            break
        text = _read_text_safe(repo_root / r.file.path, cfg.brief.max_file_bytes)
        if text is None:
            continue
        snippet = _extract_snippet(text, tokens, cfg.brief.max_snippet_lines)
        if not snippet:
            continue
        lang = r.file.language or ""
        out.append(f"### `{r.file.relpath}`\n\n```{lang}\n{snippet}\n```")
        n_files += 1
    if not out:
        return "_No text snippets available (files are binary, oversized, or empty)._"
    return "\n\n".join(out)


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
    tokens = _tokenize(task)
    ranked = rank_files(files, task, cfg, repo_root=repo_info.root)
    status = backend.status()
    plan = teacher.plan(task, context=minion_md)
    snippets = _format_snippets(ranked, repo_info.root, tokens, cfg)

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
        snippets=snippets,
        teacher_plan=_format_plan(plan),
    )


def write_brief(target_dir: Path, content: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"{ts}-brief.md"
    path.write_text(content, encoding="utf-8")
    return path
