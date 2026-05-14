# HANDOFF.md — Minion

Stato al 2026-05-14 (iterazione 6 chiusa).

## Stato git

- Branch: `main` (su `origin` come `origin/main`)
- Remote: `git@github.com:Pl1n10/minion.git`
- Identità locale: `Pl1n10 <robnovara@gmail.com>`
- Tag remoti: `v0.1.0-mvp` su `7dfb46a`, `v0.2.0` su `a59f395`, `v0.3.0` su `f2c8c44`
- Ultimi commit (vedi `git log --oneline -n 5`):
  - `f2c8c44` feat: minion teach — auto-populated MINION.md knowledge pack
  - `a59f395` feat: content-aware brief, minion update, GitHub Actions CI
  - `034a97c` docs: update HANDOFF with first commit hash and next steps
  - `7dfb46a` chore: initial MVP scaffold for Minion
- Working tree: in via di modifica per iter 4 (vedi sotto)

## Goal corrente

Iterazione 4: introdurre il concetto di **playbook** — markdown
prescrittivo per azioni ripetitive (setup git, init venv, ecc.) che
Minion serve agli agenti AI ma **non esegue**. Coerente con la hard
rule "Minion non è un coding agent": i playbook sono context, non
codice eseguito.

Iter 4 in due commit:
- **Commit 1**: template generico `src/minion/templates/playbooks/git-setup.md.tmpl`
  (committed) + versione personale `playbooks/git-setup.md` (gitignored) +
  `.gitignore` aggiornato. Zero code change.
- **Commit 2**: `teach.py` esteso per scoprire i `.tmpl` sotto
  `src/minion/templates/playbooks/` e renderizzare una sezione
  `## Playbooks` in `MINION.md`. Test + ruff verde.

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
13. Tag `v0.2.0` su `a59f395`.

### Iterazione 3 — `minion teach` (chiusa, taggata `v0.3.0` su `f2c8c44`)

14. Nuovo modulo `src/minion/teach.py` con classificatori per
    entrypoints, config, test, doc; estrazione metadata progetto da
    `pyproject.toml`/`package.json`/`Cargo.toml` via `tomllib`/`json`;
    suggerimento short list "first files to inspect"; render
    `MINION.md` a sezioni fisse.
15. Sezione `<!-- MINION:USER-NOTES:START/END -->` preservata
    cross-rerun. Estrazione robusta a marker invertiti o assenti.
16. Comando CLI `minion teach` con `--dry-run` che stampa senza
    scrivere. Errore esplicito se `.minion/` manca.
17. Template `MINION.md.tmpl` di `init` ora include i marker user-notes
    fin dal primo run, così l'utente può scrivere note prima ancora di
    chiamare `teach`.
18. Test classificatori e CLI: 44 test totali verdi. Ruff: clean.
19. Commit `f2c8c44` + push su `origin/main`. Tag `v0.3.0` pushato.

### Iterazione 4 — playbooks (in corso)

20. **Concetto**: un playbook è un file markdown prescrittivo per
    un'azione ripetitiva (setup git, init venv, scaffold modulo).
    Minion lo serve agli agenti AI come parte del knowledge pack
    — **non lo esegue**. Coerente con la hard rule "Minion non è un
    coding agent".
21. **Layout**: i template generici (con placeholders `{{...}}`) vivono
    in `src/minion/templates/playbooks/*.md.tmpl` e sono distribuiti
    col package. Le versioni personali risolte (con identità git
    dell'operatore, URL remoti, ecc.) vivono in `/playbooks/*.md`
    nella root del repo e sono **gitignored** — non distribuibili.
22. Primo playbook: `git-setup`. Generico in
    `src/minion/templates/playbooks/git-setup.md.tmpl`. Versione
    personale (Roberto) in `playbooks/git-setup.md`.
23. `teach.py` esteso: `PlaybookEntry` dataclass, `_discover_playbooks()`
    via `importlib.resources.files`, `_extract_playbook_description()`
    che pesca la prima frase del blockquote in cima al `.tmpl`, sezione
    `## Available playbooks` aggiunta a `render_minion_md`. Due test
    nuovi (discovery + render). Totale: **46 test verdi**, ruff clean.
    Smoke test E2E: `minion teach` su repo fresco mostra la sezione
    Playbooks con `git-setup` correttamente listato.
24. Commit `4b4c3d3` + tag `v0.4.0`.

### Iterazione 4.1 — pulizia upload accidentali (chiusa)

25. Rimossi via `git rm` i due file caricati per sbaglio via GitHub web
    UI durante l'inserimento del banner README: `b80eacfb-...png` nella
    root (duplicato del banner ufficiale in `assets/`) e `assets/minion`
    (1 byte). Commit `d309ae7`.

### Iterazione 5 — playbook path nei bullet (chiusa)

26. **Gap identificato**: la sezione `## Available playbooks` in
    `MINION.md` elencava nome + descrizione ma non indicava DOVE leggere
    il contenuto. Agenti non-Claude (Cursor/Codex/Aider), che non
    leggono `~/.claude/CLAUDE.md`, restavano senza coordinate.
27. **Fix**: aggiunto campo `path: str` a `PlaybookEntry`, popolato in
    `_discover_playbooks` con `str(entry)` del Traversable. Bullet ora
    rende anche \`Path: \`<full-path-to-.md.tmpl>\`\`. Aggiunta nota nella
    sezione: se esiste una versione operatore in `<minion-checkout>/playbooks/<name>.md`,
    preferirla per i parametri risolti.
28. Test esteso: `test_gather_pack_discovers_builtin_playbooks` verifica
    `path.endswith("git-setup.md.tmpl")`. `test_render_minion_md_lists_playbooks`
    verifica che `git-setup.md.tmpl` compaia nel rendered. **46 test
    verdi**, ruff clean. Smoke E2E confermato.

### Iterazione 6 — convenzione `.gitignore` per Minion (chiusa)

29. **Decisione di costo/beneficio**: cosa di `.minion/` va versionato e
    cosa no, presa testando Minion su `~/projects/pawpark` (cavia).
    - Versionati: `MINION.md` (knowledge), `config.yaml` (config),
      `teacher-plan.md` (piano editabile a mano).
    - Ignorati: `.minion/state/` (timestamps che cambiano ad ogni
      `minion update`, churn rumoroso) e `.minion/briefs/` (effimeri
      e spesso personali — non vanno nello storico condiviso).
30. Convenzione documentata nel playbook `git-setup` (sia template
    generico sia versione personale Roberto), nel pre-flight check 3.
    L'agente che segue il playbook ora include automaticamente le
    entries giuste nel `.gitignore` del progetto target.
31. Aggiornata anche `~/projects/pawpark/.gitignore` con il blocco
    Minion, e rimosso `state/manifest.json` dal repo (`git rm --cached`).

## Step in corso

Iter 6 chiusa.

## Step pending

1. (Opzionale) tag `v0.6.0` a chiusura iter 6.
2. (Follow-up) wrap reale di Repowise via `subprocess` quando il
   progetto Repowise OSS è chiarito.
3. (Idea) aggiungere a `teach` parsing di `[project.scripts]`/
   `bin` per scoprire entrypoints dichiarati e non solo per filename.
4. (Idea) playbook aggiuntivi: `python-venv-setup`, `pre-commit-setup`,
   `github-actions-ci`. Solo template generici, personalizzazione locale
   se ha senso.

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
- **`teach` non passa attraverso un Teacher provider.** Il knowledge
  pack è puramente euristico/locale. Il nome richiama il futuro
  componente Teacher ma per ora resta deterministico e offline.
  Uno step LLM-based potrà venir innestato come provider `Teacher.plan`
  che arricchisce le note utente, senza modificare la struttura del
  file.
- **`teach` salva `taught_at` nel rendering, non nel manifest.** Tenere
  due timestamp separati (`last_updated_at` per `update`, `taught_at`
  per `teach`) evita falsi positivi nei test e mantiene `update`
  manifest-only.
- **Test files non sono mai re-classificati come config**: il loop in
  `gather_pack` fa `continue` dopo un match test per evitare che es.
  `tests/test_pyproject.toml` finisca anche fra i config.
- **`.minion/**` è negli `ignore_globs` di default** del filesystem
  backend e protegge brief, manifest e config dall'auto-indicizzazione.
  Test dedicato lo presidia.
- **Teacher/Reviewer minimi di proposito**: solo interfacce + noop.
  Aggiungere prompt engineering qui sarebbe scope creep MVP.
- **Playbook system (iter 4) — Minion non li esegue**: i playbook sono
  markdown prescrittivi, serviti agli agenti AI come context. Aggiungere
  un `minion run-playbook <name>` violerebbe la hard rule "Minion non è
  un coding agent". Il template generico è committato; la versione
  parametrizzata col git identity dell'operatore è gitignored
  (`/playbooks/`) — i parametri personali non finiscono mai su origin.

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
uv run pytest -q              # atteso: 44 passed
uv run ruff check src tests   # atteso: All checks passed
```

Smoke manuale:

```bash
cd $(mktemp -d) && git init -q && echo '{"name":"d","description":"x"}' > package.json
uv run --project /home/hypn0/projects/minion minion init
uv run --project /home/hypn0/projects/minion minion teach
uv run --project /home/hypn0/projects/minion minion update
uv run --project /home/hypn0/projects/minion minion status
uv run --project /home/hypn0/projects/minion minion brief "add JWT auth"
cat .minion/MINION.md
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
