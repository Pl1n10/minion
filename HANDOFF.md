# HANDOFF.md — Minion

Stato al 2026-05-07 (iterazione 2).

## Stato git

- Branch: `main` (su `origin` come `origin/main`)
- Remote: `git@github.com:Pl1n10/minion.git`
- Identità locale: `Pl1n10 <robnovara@gmail.com>`
- Ultimi commit (vedi `git log --oneline -n 5`):
  - `034a97c` docs: update HANDOFF with first commit hash and next steps
  - `7dfb46a` chore: initial MVP scaffold for Minion
- Working tree: dirty — iter 2 da committare in unico commit `feat`

## Goal corrente

Iterazione 2 chiusa: brief davvero utile (content-aware + snippet),
nuovo comando `minion update`, CI GitHub Actions. Repowise resta
detection-only.

## Step completati

### Iterazione 1 — MVP base

1. Installato `uv` 0.11.11 in `~/.local/bin`.
2. `uv init --package` + dipendenze (typer, pyyaml, rich; dev: pytest, pytest-cov, ruff).
3. Moduli core: `config.py`, `repo.py`, `manifest.py`.
4. Backends: `base.py`, `filesystem.py` (full), `repowise.py` (detection only).
5. Teacher/Reviewer: interfacce + `noop` impl.
6. `brief.py` con ranking euristico + template markdown.
7. CLI Typer con `init`, `status`, `brief`.
8. Primo commit + push su `origin/main`.

### Iterazione 2 — brief utile + CI

9. Comando `minion update` che rinfresca manifest preservando `initialized_at`.
   `init` ora usa lo stesso helper `_refresh_manifest` e preserva anch'esso
   `initialized_at` cross-rerun (a meno di `--force`).
10. Ranking content-aware in `brief.py`: tokenizza il task, conta hit
    case-insensitive nei contenuti (whole-word regex), cap per-file per
    evitare bias da file enormi, output deterministico (filesystem
    backend ora ordina per relpath).
11. Sezione `## Snippets` nel brief: top-K file ranked vengono inclusi
    come fenced code blocks con linguaggio dedotto. Cap su numero file
    e righe via `BriefConfig.max_snippet_files` / `max_snippet_lines`.
    Skippa binary (UTF-8 strict) e oversize (`max_file_bytes`).
12. `.github/workflows/ci.yml` con `astral-sh/setup-uv@v4`, sync, ruff,
    pytest su push e PR a `main`.
13. Suite pytest: 29 test verdi. Ruff: clean.

## Step in corso

Commit unico iterazione 2 + push.

## Step pending

1. Push commit iter 2 su `origin/main`.
2. (Opzionale) tag `v0.1.0-mvp` o `v0.2.0` per allineare al brief
   davvero utile — decisione utente.
3. Verificare run CI GitHub Actions al primo push.
4. (Follow-up) wrap reale di Repowise via `subprocess` quando il
   progetto Repowise OSS è chiarito.

## Decisioni di design non ovvie

- **`auth` rimosso dalle stopwords** del ranker. In contesto codice è
  un token informativo, non rumore. Un test specifico lo protegge.
- **Repowise detection-only**: anche quando rilevato, le liste file
  arrivano dal `FilesystemBackend`. Wrapping di `repowise map` è un
  follow-up dichiarato, non un buco implementativo da nascondere.
- **`init` idempotente**: re-run non sovrascrive `MINION.md` né
  `teacher-plan.md` editati a mano. Serve `--force`. Da iter 2 anche
  `initialized_at` viene preservato cross-rerun.
- **`update` vs `init`**: `update` non ricrea file template, tocca solo
  il manifest. `init` resta il punto d'ingresso "first time".
- **Backend selection in `auto`**: priorità `repowise` se presente,
  altrimenti `filesystem`. Forzabile in `config.yaml`.
- **Content scoring capped a 5 hit per token**: senza il cap un file di
  log con migliaia di occorrenze dominerebbe il ranking. Rumore atteso
  in repo grandi.
- **Snippet generation legge direttamente dal disco**, non passa per il
  backend. Coerente con la natura del filesystem backend; quando
  Repowise verrà wrappato davvero il flusso snippet andrà rivisto.
- **`.minion/**` è negli `ignore_globs` di default** del filesystem
  backend e protegge brief, manifest e config dall'auto-indicizzazione.
  Test dedicato lo presidia.
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
uv run pytest -q              # atteso: 29 passed
uv run ruff check src tests   # atteso: All checks passed
```

Smoke manuale:

```bash
cd $(mktemp -d) && git init -q && echo '{}' > package.json
uv run --project /home/hypn0/projects/minion minion init
uv run --project /home/hypn0/projects/minion minion update
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
- Ranker content-aware ma ancora keyword-based. Per task in linguaggio
  naturale che non condividono token col codice serve embedding o
  TF-IDF; rimandato a un'iterazione futura.
- Manca tag di release (decidere se `v0.1.0-mvp` sull'iter 1 o
  `v0.2.0` sull'iter 2).
- CI Woodpecker interna: il workflow corrente è GitHub Actions; un
  porting su Woodpecker (devbox) è coerente con lo stack ma fuori
  scope ora.
