# TODO.md — Minion

> Backlog di idee per iterazioni future. Non un piano ordinato — un
> raccoglitore di osservazioni con motivazione, perché si conservi il
> *perché* oltre al *cosa*.
>
> Aggiornato: 2026-05-22 (dopo prima sessione di dogfooding su un repo terzo).

## Da dove viene questo file

Sessione del 2026-05-22: Minion usato per la prima volta come
coprocessore esterno su `pocket-dnd` (companion app D&D 5e — repo
completo allo Step 6, con `HANDOFF.md` / `STATE.md` / `CLAUDE.md` già
curati a mano). Flusso: import tarball → applicazione del playbook
`git-setup.md` → `minion init` → `minion brief` per lo Step 7 →
commit + push.

Quello che segue è quanto è emerso durante quella sessione, ordinato
per ROI atteso. Ogni voce: cosa è successo, perché serve, proposta
concreta.

## Priorità alta

### 1. Detector di stack multi-root

**Osservato.** Su pocket-dnd il manifest ha registrato `stack: []` e
il brief ha stampato "Detected stack: unknown". Eppure il repo ha
`backend/requirements.txt` (Python/FastAPI) e `frontend/package.json`
(Node/Vite). Il detector in `src/minion/repo.py` guarda solo la root.

**Perché serve.** "unknown" è la prima riga del brief che l'utente
vede. Un falso negativo visibile mina la fiducia nel tool fin dal
primo uso. La maggioranza dei repo medio-grandi ha sotto-directory
per backend/frontend/services.

**Proposta.** Estendere il detector ai marker comuni
(`pyproject.toml`, `requirements.txt`, `package.json`, `go.mod`,
`Cargo.toml`, `pom.xml`) fino a depth 2-3, su un set di nomi-tipo
(`backend/`, `frontend/`, `api/`, `web/`, `services/*`, `apps/*`,
`packages/*`). Il manifest dovrebbe registrare un elenco di
`{path, stack}` invece di una semplice lista di stringhe.

### 2. `minion brief` consuma HANDOFF.md come task implicito

**Osservato.** Per il brief sullo Step 7 ho passato a mano un task
lungo ("Step 7: aggiungere evento WebSocket add_participant + tiro
iniziativa + traccia turno corrente"). Quel testo è quasi parola per
parola la sezione `## STEP 7 — Iniziativa & turni — mini-spec` di
`HANDOFF.md`.

**Perché serve.** Il pattern HANDOFF.md è già obbligatorio nel global
CLAUDE.md di Roberto per i progetti multi-step. Se il prossimo step
è già scritto, chiedere all'utente di ricopiarlo come argomento è
ridondante e fragile (divergenza facile).

**Proposta.** Se `minion brief` viene invocato senza task e il repo
ha `HANDOFF.md`, estrarre la prima sezione `## STEP N — ...` (o
`## Step in corso`) e usarla come task. Stampare cosa è stato
estratto, per trasparenza. Un flag `--task` esplicito sovrascrive.

### 3. File "always-include" nel config

**Osservato.** Su pocket-dnd HANDOFF.md è arrivato in cima al ranking
(score 33.5) ma *solo* perché il task conteneva le parole giuste.
STATE.md, ARCHITECTURE.md e DECISIONS.md sono saliti in zona top, ma
non garantitamente. Per un task generico ("fix the login bug")
sarebbero potuti scendere sotto file di codice rumorosi.

**Perché serve.** Su un repo curato (i progetti di Roberto lo sono
quasi tutti), HANDOFF.md/STATE.md/CLAUDE.md sono *contesto
obbligatorio*, non "rilevanti se contengono le keyword giuste".

**Proposta.** In `config.yaml`, campo `brief.always_include` con una
lista di glob (es. `["HANDOFF.md", "STATE.md", "CLAUDE.md",
"DECISIONS.md"]`). Quei file vengono inclusi in una sezione `## Read
first` distinta da "Likely relevant files" (basata su ranking).
Default: `["HANDOFF.md", "STATE.md", "CLAUDE.md"]` se presenti.

## Priorità media

### 4. Snippets per simbolo, non per righe 1-40

**Osservato.** Il brief mostra le prime 40 righe di ciascun file
top-ranked. Per `backend/app/server.py` le prime 40 righe sono import
e setup del FastAPI app — la parte interessante (l'handler
`roll_request` da cui modellare il futuro `add_participant`) sta più
giù. Lo stesso per `backend/app/rooms.py`.

**Perché serve.** Snippet ciechi hanno valore solo per file brevi
(markdown) o per file dove le prime righe contano (entry point). Per
la maggior parte dei file di codice sono rumore.

**Proposta.** Per `.py`: estrarre simboli con `ast` e mostrare
funzioni/classi i cui nomi (o docstring) matchano keyword del task.
Per `.js/.ts/.jsx`: regex su `function NAME`, `const NAME =`,
`class NAME`. Fallback alle prime 40 righe se l'estrazione non trova
nulla.

### 5. Ruolo di MINION.md vs gli altri `.md` del repo

**Osservato.** `.minion/MINION.md` su pocket-dnd è restato lo stub
generato da `init`. Non ho invocato `minion teach` perché non era
chiaro cosa avrebbe popolato dato che il repo ha già `CLAUDE.md`,
`STATE.md`, `ARCHITECTURE.md`, `ANTIPATTERNS.md`, `FAILURES.md`,
`CONTEXT.md` — tutti documenti che "competono" semanticamente con
MINION.md.

**Perché serve.** O MINION.md è ridondante con la documentazione
manuale già esistente, e allora va riposizionato o eliminato; oppure
ha un ruolo distinto, e quel ruolo va comunicato chiaramente nel
README e nel template stesso.

**Proposta.** Definire esplicitamente il ruolo di MINION.md, per
esempio: *"MINION.md è una sintesi operativa auto-aggiornata che un
agente legge per primo; gli altri `.md` sono sorgenti autoritari
curati a mano, che MINION.md indicizza e cita."* `minion teach`
allora scopre i `.md` del repo, ne estrae titoli e prime righe, e li
lista in MINION.md con link al sorgente. Sezione USER-NOTES intatta.

## Priorità bassa (o speculative)

### 6. `minion check` — coerenza dello stato

**Osservato.** Il workflow dichiarato è Teacher → Minion → Reviewer,
ma due terzi (Teacher, Reviewer) sono `noop`. Manca un pezzo che
*controlli* lo stato del repo prima del prossimo step.

**Perché serve.** Il valore aggiunto del triangolo sarebbe chiudere
il loop "siamo davvero pronti per il prossimo step?". Oggi quel
controllo lo fa l'agente a mano (o non lo fa).

**Proposta.** Un comando `minion check` che valida:
`HANDOFF.md` presente e con data recente; `STATE.md` aggiornato dopo
l'ultimo commit; comando di test (estratto da CLAUDE.md sezione
"Verifying the green state") gira verde; working tree pulito. Output:
lista di check con verde/giallo/rosso. Non bloccante, informativo.
Resta coerente con la regola "Minion non è un coding agent": check ≠ fix.

### 7. `minion status` proattivo

**Osservato.** Dopo `minion init`, niente mi diceva "qui c'è un
HANDOFF.md che descrive il prossimo step, vuoi un brief?". Ho dovuto
leggermelo io e capirlo a mano.

**Perché serve.** Onboarding di un agente che apre il repo a freddo.

**Proposta.** `minion status`, oltre allo stato corrente, suggerisce
la prossima azione probabile, per esempio: *"Found `HANDOFF.md` with
section 'STEP 7'. Run `minion brief --from-handoff` to scaffold a
brief for it."*

## Roadmap playbook per livelli di universalità (sessione 2026-06-15)

**Osservato.** Aggiunti due playbook top-level: `git-setup` (già c'era) e
`tailscale-join-existing-vm` (nuovo — VM homelab già esistente che rientra sul
tailnet via authkey reusable per raggiungere un servizio interno, es. Ollama su
`pc-erica`; distinto dal `gcp-deploy/tailscale-join-vm` che fa auto-join al boot
via Terraform startup script). Discutendo "cosa altro insegnargli" è emerso che
ragionavo per *catene di deploy* invece che per *cosa tocca ogni repo*.

**Perché serve.** Il criterio "merita un playbook" è: codifica una **cicatrice o
una convenzione non ovvia**, non qualcosa che il modello già sa fare a braccio.
E i candidati vanno ordinati per **livello di universalità**, non per verticale
tecnologica. Confondere "ricorrente nei deploy" con "su tutti i progetti" porta
a scrivere i playbook nell'ordine sbagliato.

**Proposta — i playbook mancanti, per livello:**

- **L0 — ogni repo:** `git-setup` ✅.
- **L1 — ogni repo in cui si lavora davvero:**
  - `pre-commit` + ruff + mypy (il quality gate; è la cosa che si mette
    *subito dopo* git, ovunque). ⭐ primo da scrivere.
  - scaffold del doc-set + HANDOFF (CLAUDE/DECISIONS/FAILURES/STATE/HANDOFF —
    il metodo di Roberto, già obbligatorio nel global CLAUDE.md).
- **L2 — ogni repo di un dato stack:** `test-harness-bootstrap` (mock-LLM-sempre,
  PG rollback/`pytest-postgresql`, seed fissi, snapshot — regole dure già negli
  anti-pattern del global CLAUDE.md).
- **L3 — solo i repo che si deployano (catena homelab, parallela a gcp-deploy):**
  `proxmox-create-vm` (regola VMID cluster-wide + quirk template Ubuntu, già in
  `~/infra/proxmox.md`) → `vm-hardening` → `tailscale-join-existing-vm` ✅ →
  `systemd-service-deploy` → `postgres-peer-bootstrap` → `cloudflare-tunnel`.

**Note non ovvie da non perdere:**
- `systemd-service-deploy` è il più prezioso del L3: incapsula l'**incidente del
  12-06** (`rsync --delete` senza `--exclude .env` ha cancellato i secrets in
  prod). Quella regola dentro un playbook vale più di mille righe di codice.
- `vm-hardening`: scriverlo come **ruolo Ansible** (non lista bash — c'è già
  ansible-lint profilo `production`), con due profili via parametro *esposizione*
  (tailnet-only vs internet-facing). Cicatrice da codificare: hardening che
  chiude l'SSH pubblico + accesso solo-Tailscale = se Tailscale cade (urano giù
  il 15-06 ~22:22) sei murato fuori → tenere un break-glass esplicito (console
  Proxmox). E la stessa definizione-come-codice serve due scopi: *applicare* ora
  alla VM clonata, *cuocere* domani il template Ubuntu hardened (Packer/cloud-init);
  poi il playbook cambia mestiere da "applica" a "verifica drift". Quindi il
  playbook di hardening **è la strada verso l'immagine già fatta**, non un ripiego.
- `cloudflare-tunnel`: esiste già sotto `gcp-deploy/`; il meccanismo (cloudflared
  + named tunnel) è identico → **generalizzare**, non forkare. Per `tailscale` il
  fork era giustificato perché il meccanismo diverge (boot auto-join vs VM
  esistente). Decidere generalizza-vs-forka caso per caso, in base a quanto
  diverge il *meccanismo*, non il contesto.
- Token: il risparmio è il beneficio *minore* e il playbook costa token a
  caricarsi; si ripaga quando la procedura è lunga+stabile+piena di gotcha
  (hardening lo è). La motivazione vera è coerenza e non-bloccarsi-fuori.

**Cosa tenere FUORI:** la logica applicativa per-progetto (scoring SideBiz,
parsing ZFSSA, trigger Robo-PAC) — è il livello sbagliato; quello è proprio ciò
che l'assistente deve *ragionare* ogni volta, non copiare. E `gitea-woodpecker-
pipeline`: naturale ma prematuro finché Gitea non è deployato.

## Note di metodo

- Queste osservazioni vengono da **un solo** uso reale. Replicare il
  dogfooding su altri progetti (devbox-bridge, exam_audio_relay,
  moby-dick-b4, pawpark) prima di generalizzare. Lo scopo di questo
  file è ricordare il *perché* delle proposte, non implementarle in
  sequenza.
- Il punto 6 (`minion check`) è quello che potrebbe trasformare
  Minion da "coprocessore informativo" a "guardiano del workflow".
  Verificare la coerenza con la hard rule "non è un coding agent" —
  controllare lo stato non è generare codice, dovrebbe rientrare.
- I playbook (file `.md` in `playbooks/`) sono risultati più utili
  del CLI in questa sessione. Vale la pena ampliarli prima di
  aggiungere comandi al CLI? Possibile branch separato di lavoro.
- La direzione futura (vedi sezione sotto) cambia il *peso* di alcuni
  punti del backlog ma non l'elenco: il detector multi-root, il
  consumo di HANDOFF.md e `always_include` restano fondazionali a
  prescindere dal pivot esecutivo.

## Direzione futura (visione, non backlog)

> Questa sezione non è un piano di lavoro. È la stella polare che
> orienta come scegliere i prossimi step. Aggiornata 2026-05-22 dopo
> conversazione su pocket-dnd.

### Cosa Minion vuole diventare

Un **agente personale per le "cose sceme e utili"**: le operazioni
ripetitive dove la decisione è zero e la procedura è fissa, ma che
ogni volta costano attenzione perché nessuno le ha ancora messe in
un posto solo. Esempi reali:

- "Crea repo locale + GitHub + push iniziale con le mie convenzioni"
  (oggi: il playbook `git-setup.md` lo *descrive*, non lo *fa*).
- "Cloneme la VM template FastAPI su Proxmox `urano`, assegnale un
  IP statico, registrale il sottodominio via Cloudflare Tunnel,
  installale il systemd unit standard".
- "Crea un cron Woodpecker per questo repo Gitea con la mia pipeline
  standard Python/uv/pytest".
- "Snapshot Proxmox + dump Postgres prima del deploy del SideBiz Agent".

Minion sa **come Roberto vuole queste cose fatte**, perché le sue
convenzioni sono codificate nei playbook e nei template. Il valore
non è "Minion sa fare il deploy" — Ansible e Terraform già lo fanno.
Il valore è "Minion sa fare il deploy *come piace a te*, senza
ricontrattare ogni volta i dettagli".

### Cosa NON cambia rispetto alle hard rule attuali

Le tre hard rule del `CLAUDE.md` di Minion vanno lette per cosa
dicono davvero, non per la loro etichetta:

1. *"Don't turn Minion into a coding agent. No code generation."* —
   parla del **codice del repo target**. Deployare un template
   Proxmox è applicare un artefatto preconfezionato a un'infra:
   non è generazione di codice e non viola questa regola.
2. *"Don't add a coding step to the CLI"* — gli esempi citati
   (`minion fix`, `minion apply`) si riferiscono a modifiche al
   sorgente. `minion deploy` / `minion provision` sono comandi
   infrastrutturali, non rientrano.
3. *"MVP must remain offline-capable"* — questa **sì** è in
   conflitto col toccare Proxmox/Cloudflare API. È un vincolo di
   scope-MVP che cade quando si esce dall'MVP. Va riscritta come
   *"i comandi di lettura (`init`, `brief`, `teach`, `status`)
   restano offline-capable; i comandi di esecuzione (`run`,
   `deploy`, `provision`) possono parlare con API esterne purché
   credenziali e endpoint siano configurabili"*.

### Forma proposta

Un binario unico `minion` con due famiglie di sottocomandi marcate
nel nome:

- **Read-only** (oggi): `minion init`, `minion brief`, `minion teach`,
  `minion status`, `minion update`. Nessun side effect fuori dal
  repo corrente. Restano offline-capable.
- **Effects** (futuro): `minion run <playbook>`, `minion deploy <template>`,
  `minion provision <target>`. Side effect espliciti, idempotenti
  dove possibile, dry-run di default per i comandi di deploy.

Per la lista lunga di "cose sceme", prima di costruire un proprio
runner, **provare a scoprire ed eseguire automazioni esistenti**:
`Makefile` targets, npm scripts, `scripts/*.sh` nei progetti. Un
`minion run --list` che indicizza queste fonti è probabilmente il
primo passo a costo zero che valida l'ipotesi prima di scrivere un
motore proprio.

Per il deploy Proxmox / Cloudflare / Gitea: **wrapper opinionati**
sopra Ansible (`community.general.proxmox*`) o Terraform (provider
Telmate per Proxmox, ufficiale per Cloudflare). I template, le
convenzioni di naming, gli IP range, i sottodomini standard sono
codificati in YAML/HCL nei `playbooks/` con parametri risolti dalla
sezione personale (come oggi `git-setup.md`).

### Discovery dei playbook deve diventare ricorsiva (e raggruppare famiglie)

**Osservato (2026-05-31).** Aggiunta la prima *famiglia* di playbook,
`templates/playbooks/gcp-deploy/` (INDEX + 7 `.md.tmpl`: project
bootstrap, terraform VM, tailscale join, ghcr publish, cloudflare
tunnel, ansible provision, oauth wiring). Nata dal deploy reale di
toto-mondiale, il cui `infra/` (Terraform + Ansible) è l'istanza
concreta che questi runbook descrivono — pattern "codice-nel-repo,
playbook-spiega".

**Perché serve.** `_discover_playbooks()` in `teach.py` fa
`root.iterdir()` (solo top-level) e quindi NON vede i playbook nelle
sottocartelle: la famiglia `gcp-deploy/` esiste ma non emerge in
`minion teach`. Finché il discovery resta flat, le famiglie sono solo
documentazione di riferimento, non sono indicizzate nel MINION.md.

**Proposta.** Rendere il discovery ricorsivo (`rglob("*.md.tmpl")`),
derivare lo `slug` dal path relativo (es. `gcp-deploy/terraform-gce-vm`),
e nel rendering raggruppare per cartella-famiglia con l'`INDEX.md` (se
presente) come intestazione. Aggiornare `test_teach.py` di conseguenza
(oggi asserisce solo che `git-setup` è presente, quindi non si rompe,
ma andrebbe esteso per coprire le famiglie).

### Hard rule del CLAUDE.md di Minion da rivedere

Quando si arriva a iniziare il lavoro su `minion run`, **prima cosa**:
riscrivere la sezione "Hard rules" del `CLAUDE.md` di Minion per
chiarire la distinzione codice-del-repo vs infrastruttura, e per
spostare "offline-capable" dal livello di principio al livello di
sottocomandi read-only. Senza quell'aggiornamento, la prossima
sessione che apre il repo si trova davanti regole che vietano
proprio il pivot deciso, e o le rispetta (bloccando il lavoro) o le
ignora (creando incoerenza).
