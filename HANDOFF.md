# HANDOFF.md — Minion

Stato al 2026-05-07.

## Stato git

- Branch: `main` (default uv init)
- Ultimo commit: pending — primo commit MVP da fare
- Working tree: dirty (intero scaffold da committare)

## Goal corrente

Chiudere l'MVP: `minion init/status/brief` funzionanti su qualunque repo,
con backend filesystem solido e Repowise come detection opzionale.

## Step completati

1. Installato `uv` 0.11.11 in `~/.local/bin`.
2. `uv init --package` + dipendenze (typer, pyyaml, rich; dev: pytest, pytest-cov, ruff).
3. Moduli core: `config.py`, `repo.py`, `manifest.py`.
4. Backends: `base.py`, `filesystem.py` (full), `repowise.py` (detection only).
5. Teacher/Reviewer: interfacce + `noop` impl.
6. `brief.py` con ranking euristico + template markdown.
7. CLI Typer con `init`, `status`, `brief`.
8. Suite pytest: 23 test verdi. Ruff: clean.
9. README + CLAUDE.md + HANDOFF.md (questo file).

## Step in corso

Primo commit MVP. Il repo è già un git repo (creato da `uv init`) ma
nulla è stato committato.

## Step pending

1. `git add` + primo commit MVP.
2. (Opzionale) tag `v0.1.0-mvp`.
3. Decidere se pubblicare su Gitea/GitHub e con quale nome.

## Decisioni di design non ovvie

- **`auth` rimosso dalle stopwords** del ranker. In contesto codice è
  un token informativo, non rumore. Un test specifico lo protegge.
- **Repowise detection-only**: anche quando rilevato, le liste file
  arrivano dal `FilesystemBackend`. Wrapping di `repowise map` è un
  follow-up dichiarato, non un buco implementativo da nascondere.
- **`init` idempotente**: re-run non sovrascrive `MINION.md` né
  `teacher-plan.md` editati a mano. Serve `--force`.
- **Backend selection in `auto`**: priorità `repowise` se presente,
  altrimenti `filesystem`. Forzabile in `config.yaml`.
- **Teacher/Reviewer minimi di proposito**: solo interfacce + noop.
  Aggiungere prompt engineering qui sarebbe scope creep MVP.

## Workflow concordato con l'utente

- Comunicazione in italiano.
- Filesystem backend prima e solido; Repowise solo detection.
- `.minion/` lifecycle affidabile e idempotente.
- Test verdi prima di considerare uno step "done".
- `HANDOFF.md` aggiornato a fine step, non a fine turno.
- Commit allineato al codice (uno step = un commit).

## Come verificare lo stato verde

```bash
cd /home/hypn0/projects/minion
uv sync
uv run pytest -q              # atteso: 23 passed
uv run ruff check src tests   # atteso: All checks passed
```

Smoke manuale:

```bash
cd $(mktemp -d) && git init -q && echo '{}' > package.json
uv run --project /home/hypn0/projects/minion minion init
uv run --project /home/hypn0/projects/minion minion status
uv run --project /home/hypn0/projects/minion minion brief "add JWT auth"
ls .minion/briefs/
```

## File da leggere per riprendere il filo (in ordine)

1. `~/.claude/CLAUDE.md` (global)
2. `./CLAUDE.md` (repo)
3. `./HANDOFF.md` (questo file)
4. `git log --oneline -n 5`
5. `git status`
6. `src/minion/cli.py` per il giro CLI

## Known issues / follow-up

- Repowise wrapping reale: implementare `RepowiseBackend.list_files()`
  via subprocess su `repowise map` (o equivalente) appena il progetto
  Repowise OSS è chiarito.
- Il ranker è puramente token-in-path. Su repo grandi può essere
  inutile per task espressi in linguaggio naturale lontano dai
  filename. Considerare TF-IDF su contenuti (cap dimensione file).
- Manca tag `v0.1.0-mvp` in git.
- Manca CI (Woodpecker pipeline) — coerente con lo stack devbox ma
  fuori scope MVP.
