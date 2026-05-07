# Minion

> Local-first **repo intelligence coprocessor** for AI coding agents.
>
> **What this is not:** a coding agent. Minion does not write code,
> open files for you, or call cloud LLMs by itself.
>
> **What this is:** a thin orchestration layer that sits next to your
> repo, indexes it, and produces structured *briefs* you can hand to
> any coding assistant — Claude Code, Codex, Cursor, Aider, your own
> custom agent — to give it durable, repo-aware context.

The eventual workflow is **Teacher → Minion → Reviewer**:

- **Teacher** turns a high-level task into a plan.
- **Minion** (this CLI) gathers the repo facts the assistant needs.
- **Reviewer** checks the resulting diff against the plan.

Today only the Minion side ships. Teacher and Reviewer are wired as
pluggable interfaces with no-op providers.

## Install

```bash
# Using uv (recommended)
uv tool install --from . minion        # global tool
# or, from a checkout
uv sync
uv run minion --help
```

Requires Python 3.12+.

## Commands

```bash
minion init                         # set up .minion/ in the current repo
minion teach                        # populate .minion/MINION.md from the repo
minion update                       # refresh manifest (git, stack, backends)
minion status                       # show detected stack + backend availability
minion brief "add JWT auth flow"    # generate a markdown brief for a task
```

### Teaching the repo to itself

`minion teach` regenerates `.minion/MINION.md` from a scan of the repo:

- project name + description (from `pyproject.toml`, `package.json`, or
  `Cargo.toml`)
- detected stack
- key entrypoints, config files, test files, documentation files
- suggested first files to inspect
- ignored / do-not-index paths

A user-editable section between
`<!-- MINION:USER-NOTES:START -->` and `<!-- MINION:USER-NOTES:END -->`
is **preserved across runs**. Use it for durable notes (purpose,
ground rules, conventions) that should not be auto-overwritten.

`minion teach --dry-run` prints the rendered MINION.md to stdout
without touching the file.

### File layout after init

`minion init` creates:

```
.minion/
├── MINION.md                # durable repo notes (edit me)
├── teacher-plan.md          # living plan, edited by Teacher / by hand
├── config.yaml              # backends, providers, ignore globs
├── briefs/                  # one markdown file per `minion brief` call
└── state/
    └── manifest.json        # init metadata + backend availability
```

## Backends

Minion talks to the repo through a **backend interface**. Backends in
the MVP:

| Backend     | Status     | Notes                                            |
|-------------|------------|--------------------------------------------------|
| `filesystem`| ✅ default | Walks the repo, language-tags by extension       |
| `repowise`  | 🟡 detect  | Detects the `repowise` CLI on PATH (no deep wrap)|

Selection order is `auto`: prefer `repowise` if present, else
`filesystem`. Force a specific backend in `.minion/config.yaml`:

```yaml
backend:
  preferred: filesystem   # or: auto, repowise
  repowise_binary: repowise
```

Adding a new backend = subclass `RepoBackend` in
`src/minion/backends/`.

## Teacher and Reviewer

Both are pluggable through `select_teacher` / `select_reviewer`. The
shipped providers are `noop`, which return deterministic placeholder
output. Wire a real provider (OpenRouter, Ollama, OpenAI, Anthropic)
by adding a class under `src/minion/teacher/` or
`src/minion/reviewer/` and dispatching from the package `__init__`.

## Brief format

A brief is a single markdown file under `.minion/briefs/`. It includes:

- the task as you wrote it
- repo snapshot (root, branch, head, detected stack)
- a heuristic-ranked list of likely relevant files
- short snippets of the top-ranked files (size-bounded, UTF-8 only)
- a Teacher plan section (placeholder until a real provider is wired)

Heuristics in the MVP: token-in-path matching, token-in-content matching
(capped per file), source-file boost, entry-point boost, large-file
penalty. Files are sorted deterministically before ranking. Tune
weights and limits in `src/minion/brief.py` and the `brief.*` block of
`.minion/config.yaml`:

```yaml
brief:
  max_files: 25            # ranked entries shown
  max_file_bytes: 200000   # skip files bigger than this for content scan/snippets
  max_snippet_files: 5     # how many top files get a snippet
  max_snippet_lines: 40    # lines per snippet
  ignore_globs: [...]      # never indexed (includes .minion/**)
```

## Development

```bash
uv sync                          # install deps + dev deps
uv run pytest -q                 # run tests
uv run ruff check src tests      # lint
```

## Project layout

```
src/minion/
├── cli.py
├── config.py
├── manifest.py
├── repo.py
├── brief.py
├── backends/
│   ├── base.py
│   ├── filesystem.py
│   └── repowise.py
├── teacher/
│   ├── base.py
│   └── noop.py
├── reviewer/
│   ├── base.py
│   └── noop.py
└── templates/
tests/
```

## License

TBD.
