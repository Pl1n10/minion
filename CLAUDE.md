# CLAUDE.md — Minion (local repo)

> Loaded automatically when Claude Code opens this repo.
> Complements `~/.claude/CLAUDE.md` (global) and `HANDOFF.md` (state).

## What this project is

A Python CLI (`minion`) that acts as a **repo intelligence coprocessor**
for AI coding agents. It is *not* itself a coding agent — it produces
structured briefs that humans hand to coding assistants.

Workflow it serves: **Teacher → Minion → Reviewer**. Teacher and
Reviewer are wired as interfaces with `noop` implementations only.

## Hard rules

- **Do not turn Minion into a coding agent.** No code generation, no
  cloud LLM calls in `init` / `status` / `brief`. The MVP must remain
  offline-capable.
- **Backends must be modular.** New backends subclass `RepoBackend`.
  Never special-case a backend in `cli.py` or `brief.py`.
- **Repowise stays optional.** Detection only in MVP. Briefs must work
  identically whether Repowise is on PATH or not.
- **Teacher / Reviewer interfaces stay thin.** No prompt engineering,
  no retries, no provider-specific logic in `base.py`.

## Stack and conventions

- Python 3.12, packaged with `uv` (uv_build backend).
- CLI: Typer + Rich.
- Config: `.minion/config.yaml`, parsed via PyYAML into dataclasses.
- Tests: pytest only, `typer.testing.CliRunner` for CLI assertions.
- Lint: ruff.
- No emojis in code or docs unless asked.

## Layout

```
src/minion/
  cli.py              # Typer app
  config.py           # MinionConfig + YAML I/O
  manifest.py         # state/manifest.json schema + I/O
  repo.py             # git + stack detection
  brief.py            # ranking + markdown rendering
  backends/{base,filesystem,repowise}.py
  teacher/{base,noop}.py
  reviewer/{base,noop}.py
  templates/*.tmpl    # MINION.md, teacher-plan.md, brief.md
tests/                # pytest with tmp_repo / tmp_git_repo fixtures
```

## Verifying the green state

```bash
uv sync
uv run pytest -q
uv run ruff check src tests
```

Optional manual smoke:

```bash
cd /tmp && rm -rf m && mkdir m && cd m && git init -q && \
  echo '{}' > package.json && \
  uv run --project /home/hypn0/projects/minion minion init && \
  uv run --project /home/hypn0/projects/minion minion brief "test"
```

## Decisions worth remembering

- `auth` is **not** a stopword in the brief ranker. It looked too
  generic at first, but in code-search context it is one of the most
  load-bearing tokens. Removing it caused a test failure that proved
  the point.
- The Repowise backend, even when detected, currently sources files
  from the filesystem fallback. Wiring `repowise map` output is a
  follow-up — keep that path obvious.
- `minion init` is idempotent unless `--force` is passed. User-edited
  `MINION.md` and `teacher-plan.md` must survive a re-run.

## What NOT to do

- Don't add a coding step to the CLI ("minion fix", "minion apply").
  That belongs to the assistant the brief is handed to, not to Minion.
- Don't shell out to any cloud API in MVP code paths.
- Don't introduce a non-Typer CLI framework.
- Don't break the manifest JSON shape without a version bump.
